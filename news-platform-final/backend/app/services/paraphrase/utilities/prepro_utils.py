import pickle
import numpy as np
from nltk.tokenize import word_tokenize
import nltk
import os

# Root of the backend project where vocab.txt is copied
VOCAB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'vocab.txt')

def replace_NNP(txt):
    tagged_tokens = nltk.pos_tag(txt)
    output = []
    proper_nouns = []
    for i, w in enumerate(txt):
        if i < len(tagged_tokens) and tagged_tokens[i][1] == 'NNP':
            output.append('UNK')
            proper_nouns.append(w)
        else:
            output.append(w)
    return output, proper_nouns

def prepro_input(input_sent, max_len=26):
    if not os.path.exists(VOCAB_PATH):
        # Return empty/dummy if vocab not found
        return np.zeros(max_len), {}, {}, [], 0

    with open(VOCAB_PATH, 'rb') as vocab_open:
        vocab = pickle.load(vocab_open)
    
    itow = {i+1:w for i,w in enumerate(vocab)}
    wtoi = {w:i+1 for i,w in enumerate(vocab)}
    if 0 not in itow:
        itow[0] = 'UNK'

    dict_len = len(itow)
    EOS, PAD, SOS = dict_len, dict_len + 1, dict_len + 2
    itow[EOS], itow[SOS], itow[PAD] = '<EOS>', '<SOS>', '<PAD>'
    wtoi['<EOS>'], wtoi['<SOS>'], wtoi['<PAD>'] = EOS, SOS, PAD

    sent = word_tokenize(input_sent)
    sent_len = len(sent)
    sent, pn = replace_NNP(sent)

    for i, word in enumerate(sent):
        sent[i] = (word if word in vocab else 'UNK')

    input_array = np.zeros(max_len, dtype='uint32')
    for i, word in enumerate(sent):
        if i < max_len:
            input_array[i] = wtoi.get(word, wtoi['UNK'])

    return input_array, wtoi, itow, pn, sent_len
