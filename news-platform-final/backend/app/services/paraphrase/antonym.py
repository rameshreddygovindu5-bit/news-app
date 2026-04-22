import nltk
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from nltk.corpus import wordnet as wn
import logging

logger = logging.getLogger(__name__)

# Ensure NLTK resources are available
for res in ['punkt', 'averaged_perceptron_tagger', 'wordnet']:
    try:
        nltk.data.find(f'tokenizers/{res}' if res == 'punkt' else f'taggers/{res}' if 'tagger' in res else f'corpora/{res}')
    except LookupError:
        nltk.download(res, quiet=True)

class Antonym():
  def __init__(self, sentence):
    self.sentence = sentence

  def pos(self, tag):
    if tag.startswith('NN'):
      return wn.NOUN
    elif tag.startswith('V'):
      return wn.VERB
    return None

  def antonyms(self, word, tag):
    antonyms = set()
    wn_pos = self.pos(tag)
    if not wn_pos: return None

    for syn in wn.synsets(word, pos=wn_pos):
      for lemma in syn.lemmas():
        for antonym in lemma.antonyms():
          antonyms.add(antonym.name())
    
    if len(antonyms):
      return list(antonyms)[0]
    return None

  def main(self):
    if not self.sentence: return ""
    try:
        words = self.sentence.split(' ')
        l, i = len(words), 0
        tagged_words = pos_tag(words)
        output = []

        while i < l:
          word = words[i]
          new_word = word
          if word.lower() == 'not' and i + 1 < l:
            antonym = self.antonyms(words[i+1], tagged_words[i+1][1])
            if antonym != None:
              new_word = antonym
              i += 1 # skip next word
          output.append(new_word)
          i += 1
        return " ".join(output)
    except Exception as e:
        logger.error(f"Error in Antonym modification: {e}")
        return self.sentence
