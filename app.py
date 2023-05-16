from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import requests
import xmltodict
import os
from datetime import datetime
import os
import logging
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Import(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    importDate = db.Column(db.DateTime, nullable=False)
    rawContent = db.Column(db.Text, nullable=False)

class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    externalId = db.Column(db.String(500), unique=True, nullable=False)
    importDate = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=False)
    publicationDate = db.Column(db.DateTime, nullable=False)
    link = db.Column(db.Text, nullable=False)
    mainPicture = db.Column(db.Text, nullable=False)

with app.app_context():
    db.create_all()




@app.route('/api/articles/import', methods=['POST'])
def import_articles():
    site_rss_url = request.args.get('siteRssUrl')
    response = requests.get(site_rss_url)

    if response.status_code != 200:
        return jsonify({'message': 'Error retrieving RSS feed.'}), 500

    try:
        data = xmltodict.parse(response.content)
    except Exception as e:
        logging.error(f'Error parsing XML: {e}')
        return jsonify({'message': 'Error parsing XML.'}), 500

    new_import = Import(importDate=datetime.now(), rawContent=str(data))
    db.session.add(new_import)

    try:
        items = data['rss']['channel']['item']
    except KeyError:
        return jsonify({'message': 'Invalid XML format: missing required elements.'}), 400

    for item in items:
        article = Article.query.filter_by(externalId=item['guid']).first()
        if article:
            article.title = item['title']
            article.description = item['description']
            article.publicationDate = datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z")
            article.link = item['link']
            article.mainPicture = item.get('enclosure', {}).get('@url', 'default_picture_url')
        else:
            new_article = Article(
                externalId=item['guid'],
                importDate=datetime.now(),
                title=item['title'],
                description=item['description'],
                publicationDate=datetime.strptime(item['pubDate'], "%a, %d %b %Y %H:%M:%S %Z"),
                link=item['link'],
                mainPicture=item.get('enclosure', {}).get('@url', 'default_picture_url')
            )
            db.session.add(new_article)

    db.session.commit()
    return jsonify({'message': 'Import successful.'}), 200


def get_word_with_most_vowels(string):
    words = string.split(' ')
    max_vowels = 0
    word_with_max_vowels = ''

    for word in words:
        vowel_count = sum([1 for letter in word.lower() if letter in 'aeiouy'])
        if vowel_count > max_vowels or (vowel_count == max_vowels and len(word) > len(word_with_max_vowels)):
            max_vowels = vowel_count
            word_with_max_vowels = word

    return word_with_max_vowels

@app.route('/api/articles', methods=['GET'])
def get_articles():
    articles = Article.query.all()
    return jsonify([{
        'id': article.id,
        'externalId': article.externalId,
        'importDate': article.importDate,
        'title': article.title,
        'description': article.description,
        'publicationDate': article.publicationDate,
        'link': article.link,
        'mainPicture': article.mainPicture,
        'wordWithMostVowels': get_word_with_most_vowels(article.title)
    } for article in articles]), 200

@app.route('/', methods=['GET'])
def home() :
    return "hello world"


if __name__ == "__main__":
    app.run(debug=True)