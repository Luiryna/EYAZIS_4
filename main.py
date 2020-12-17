import sys
from PyQt5 import QtWidgets
import json
import requests
import psycopg2
import nltk
import main_window, widget
import spacy
import re
from nltk.tokenize import sent_tokenize
from nltk import CFG

con = psycopg2.connect(
    database="eyazis4",
    user="postgres",
    password="6001",
    host="localhost",
    port="5432"
)


class Dialog(QtWidgets.QDialog, widget.Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class Application(QtWidgets.QMainWindow, main_window.Ui_MainWindow):
    word_tf = {}
    word_info = {}

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.dialog = None
        self.chooseFileButton.clicked.connect(self.browse_file)
        self.addDictButton.clicked.connect(self.add_to_dict)
        self.deleteDictButton.clicked.connect(self.delete_dict)
        self.translateDictButton.clicked.connect(self.translate_dict)
        self.saveButton.clicked.connect(self.save_file)
        self.viewInfoButton.clicked.connect(self.get_information)
        self.treeDraw.clicked.connect(self.draw)

    def draw(self):
        num = int(self.lineEdit.text())
        simple_grammar = """NP: {<DT>?<JJ>*<NN>}
                           VBD: {<VBD>}
                           IN: {<IN>}"""
        parser_chunking = nltk.RegexpParser(simple_grammar)
        text = self.originalText.toPlainText()
        sentences = sent_tokenize(text)
        # sent_text = nltk.word_tokenize(sents)
        pos_text = nltk.pos_tag(sentences[num - 1].split())
        parser_chunking.parse(pos_text)
        Output_chunk = parser_chunking.parse(pos_text)
        Output_chunk.draw()

    def browse_file(self):

        file = QtWidgets.QFileDialog.getOpenFileName(self, 'Выберите файл', "*.txt")[0]
        if file:
            openfile = open(file, 'r')
            with openfile:
                self.originalText.setText(openfile.read())

    def translate_dict(self):
        # nltk.download('averaged_perceptron_tagger')
        self.word_info = {}
        self.word_tf = {}
        words_count = 0
        nlp = spacy.load("en_core_web_sm")
        text = self.originalText.toPlainText()
        data = {
            'folder': 'b1g4j9jtpjtc59p29jgl',
            'sourceLanguageCode': 'en',
            'targetLanguageCode': 'ru',
            'texts': text,
            'folderId': 'b1g4j9jtpjtc59p29jgl',
        }
        words = self.get_words(text)
        print(words)
        self.word_tf = self.get_tf(words)
        cur = con.cursor()
        cur.execute("SELECT * FROM dict")
        for row in cur:
            result = re.findall(row[1], text, re.IGNORECASE)
            if result:
                words_count += len(result)
                word = nlp(result[0])
                for token in word:
                    self.word_info[token.text] = token.lemma_ + ' ' + token.pos_
                    # print('hi')
                text = re.sub(row[1], row[2], text, flags=re.IGNORECASE)
        cur.close()
        print(data)
        self.send(data)

    def get_information(self):
        sfile = open('words_info.txt', 'w')
        with sfile:
            sfile.write('Частота слов:\n')
            for word, tf in self.word_tf.items():
                sfile.write(word + ' - ' + str(tf) + '\n')
            # sfile.write(str(self.word_tf))
            sfile.write('************ \n')
            sfile.write('Информация о словах из словаря:\n')
            sfile.write('************ \n')
            if len(self.word_info) == 0:
                sfile.write('Совпадений со словарем не обнаружено\n')
            else:
                for word, info in self.word_info.items():
                    sfile.write(word + ' - ' + info + '\n')
            # sfile.write(str(self.word_info))

    def send(self, data):
        url = 'https://translate.api.cloud.yandex.net/translate/v2/translate'
        headers_dict = {
            'Authorization': 'Api-Key AQVN3Tv8v9fQmVnbsHDyOfgSa_9hDpdUTC7mEwhr'
        }
        json_data = json.dumps(data)
        r = requests.post(url, headers=headers_dict, data=json_data)
        response_json = r.json()
        self.translatedText.setText(response_json['translations'][0]['text'])

    def get_words(self, text):
        words = {}
        for raw_word in text.split():
            if raw_word.endswith((',', '.', '-', '!', '?', ';', '»', ')', '”', ':')):
                raw_word = raw_word[:-1]
            if raw_word.startswith(('«', '(', '“')):
                raw_word = raw_word[1:]
            word = raw_word
            if word in words:
                words[word] += 1
            else:
                words[word] = 1
        return words

    def get_tf(self, words):
        max_count = 0
        for count in words.values():
            max_count += count
        tf_dict = {}
        for word in words:
            tf_dict[word] = round(words[word] / max_count, 4)
        sorted_tf_dict = {key: v for key, v in sorted(tf_dict.items(), key=lambda item: item[1], reverse=True)}
        return sorted_tf_dict

    def add_to_dict(self):
        file_name = QtWidgets.QFileDialog.getOpenFileName(self, 'Выберите файл', "*.txt")[0]
        cur = con.cursor()
        if file_name:
            openfile = open(file_name, 'r')
            with openfile:
                for line in openfile:
                    line_words = line.split(' - ')
                    cur.execute("INSERT INTO dict(engwrd, ruswrd) VALUES (%s, %s)", (line_words[0], line_words[1][:-1]))
                    con.commit()
        cur.close()
        self.dialog = Dialog()
        self.dialog.show()
        self.dialog.textEdit.setText('Записи были добавлены')

    def delete_dict(self):
        cur = con.cursor()
        cur.execute("DELETE FROM dict")
        cur.close()
        self.dialog = Dialog()
        self.dialog.show()
        self.dialog.textEdit.setText('Записи удалены')

    def save_file(self):
        text = self.translatedText.toPlainText()
        sfile = open('translated.txt', 'w')
        with sfile:
            sfile.write(text)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Application()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
