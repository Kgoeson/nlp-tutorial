import os
import re
import argparse
import unicodedata
import numpy as np
import pandas as pd
import dataLoader as loader
import embedding as embed

GLOVE = 'glove.6B.100d.txt'

def argparser():
    p = argparse.ArgumentParser()

    p.add_argument('--filename',
                    default = 'Posts.xml')
    
    config = p.parse_args()

    return config

class Tokenizer:
    def __init__(self, input):
        self.input = input
        self.word2index = {}
        self.index2word = {}
        self.word2count = {}
        self.n_words = 0

    def unicodeToAscii(self, s): 
        # Turn a Unicode string to plain ASCII
        # refer to https://stackoverflow.com/a/518232/2809427
        return ''.join( c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    def normalizeString(self, s):
        # lowercase, trim and remove non-letter characters
        s = self.unicodeToAscii(s.lower().strip())
        s = re.sub(r"([.!?])", r" \1", s)
        s = re.sub(r"[^a-zA-Z.!?]+", r" ", s)
        return s

    def build_vocab(self):
        for paragraph in self.input:
            for sentence in paragraph.splitlines():
                sentence = self.normalizeString(sentence)
                for word in sentence.split(' '): # tokenizing
                    if word not in self.word2index:
                        self.word2index[word] = self.n_words
                        self.index2word[self.n_words] = word
                        self.word2count[word] = 1
                        self.n_words += 1
                    else:
                        self.word2count[word] += 1

def clean_tag(input):
    cleaner = re.compile('<.*?>')
    return re.sub(cleaner, '', input)

def clean_url(input):
    return re.sub(r'http\S+', '', input)

def cleaning(input, drop):
    # Remove tags, url
    input.body = input.body.apply(lambda x: clean_tag(x))    
    input.body = input.body.apply(lambda x: clean_url(x))    

    # Drop only if NaN in title/body column
    if drop:
        input = input.dropna(subset=['title', 'body'])

    # Type conversion
    pd.options.mode.chained_assignment = None
    input.title = input.title.fillna('').astype('str').str.strip()
    input.tags = input.tags.fillna('').astype('str').str.strip()
    input.body = input.body.fillna('').astype('str').str.strip()
    input.posttypeid = input.posttypeid.astype('int')
    input.viewcount = input.viewcount.astype('float')

    return input

def compute_tf_idf(input):
    tokenizer = Tokenizer(input.body+input.title)
    tokenizer.build_vocab()
    
    # Compute TF-IDF 
    tfidf = {word: np.log(tokenizer.n_words/count) for (word, count) in tokenizer.word2count.items()}

    tfidf_matrix = np.zeros((len(tokenizer.word2index), 1))
    # |tfidf_matrix| = (n_words, 1)
    for word, idx in tokenizer.word2index.items():
        tfidf_matrix[idx] = tfidf[word]

    return tokenizer, tfidf_matrix

def download_glove():
    if not os.path.exists('data/{}'.format(GLOVE)):
        import wget
        wget.download('https://storage.googleapis.com/deep-learning-cookbook/'+GLOVE,
                        'data/'+GLOVE)
        print('[Glove] Downloaded to : data/{}'.format(GLOVE))

def preprocessing(input, clean_drop=False):
    # Cleaning
    input = cleaning(input, clean_drop)

    # Compute TF-IDF and get TF-IDF matrix
    tokenizer, tfidf_matrix = compute_tf_idf(input)

    # Download pre-trained Glove word vectors.
    download_glove()
    
    # Get embedding matrix with pre-trained word representations
    word_emb_matrix = embed.word_embedding_matrix(word2index = tokenizer.word2index,
                                                  embedding_path = 'data/{}'.format(GLOVE),
                                                  embedding_dim = 100)
    
    return input, tokenizer, word_emb_matrix, tfidf_matrix

if __name__=='__main__':
    config = argparser()

    data = loader.to_dataframe('data/'+config.filename)
    input, tokenizer, word_emb_matirx, tfidf_matrix = preprocessing(input = data,
                                                                    clean_drop = False)