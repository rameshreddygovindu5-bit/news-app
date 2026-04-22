import nltk
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from nltk.corpus import wordnet as wn
import logging

try:
    import spacy_universal_sentence_encoder
    nlp_use = spacy_universal_sentence_encoder.load_model('en_use_lg')
except ImportError:
    nlp_use = None

try:
    from lemminflect import getInflection
except ImportError:
    getInflection = None

logger = logging.getLogger(__name__)

# Ensure NLTK resources are available
for res in ['punkt', 'averaged_perceptron_tagger', 'wordnet', 'omw-1.4']:
    try:
        nltk.data.find(f'tokenizers/{res}' if res == 'punkt' else f'taggers/{res}' if 'tagger' in res else f'corpora/{res}')
    except LookupError:
        nltk.download(res, quiet=True)

class Synonym():
  def __init__(self, sentence):
    self.sentence = sentence
  
  def is_eligible(self, tag):
    """Only replace nouns, verbs and adjectives."""
    return tag.startswith('NN') or tag.startswith('VB') or tag.startswith('JJ')

  def get_wn_pos(self, tag):
    if tag.startswith('NN'): return wn.NOUN
    if tag.startswith('V'): return wn.VERB
    if tag.startswith('J'): return wn.ADJ
    return None

  def get_candidates(self, word, tag):
    wn_pos = self.get_wn_pos(tag)
    if not wn_pos:
        return set()
    
    synsets = wn.synsets(word, pos=wn_pos)
    candidates = set()
    for ss in synsets:
        for lemma in ss.lemmas():
            name = lemma.name().lower()
            if name != word.lower() and '_' not in name:
                candidates.add(name)
    return candidates

  def inflect_word(self, candidate, original_tag):
    """Inflect the candidate synonym to match the original word's grammatical form."""
    if getInflection:
        inflected = getInflection(candidate, tag=original_tag)
        if inflected:
            return inflected[0]
    return candidate

  def get_best_synonym(self, word, tag, sentence, candidates, threshold=0.92):
    if not nlp_use:
        # Fallback if USE is not available: just pick the first candidate
        return list(candidates)[0] if candidates else word

    try:
        sent1 = nlp_use(sentence)
        best_candidate = word
        best_score = 0
        original_tokens = word_tokenize(sentence)
        
        for cand in candidates:
            inflected_cand = self.inflect_word(cand, tag)
            new_tokens = [inflected_cand if t == word else t for t in original_tokens]
            sent2_text = ' '.join(new_tokens)
            sent2 = nlp_use(sent2_text)
            
            score = sent1.similarity(sent2)
            if score > best_score and score > threshold:
                best_score = score
                best_candidate = inflected_cand
        return best_candidate
    except Exception as e:
        logger.error(f"Error in get_best_synonym: {e}")
        return word

  def main(self):
    if not self.sentence: return ""
    try:
        words = word_tokenize(self.sentence)
        tagged = pos_tag(words)
        output = []
        
        for word, tag in tagged:
          if not self.is_eligible(tag) or len(word) < 3:
            output.append(word)
            continue
          
          candidates = self.get_candidates(word, tag)
          if candidates:
            current_threshold = 0.94 if tag.startswith('NN') else 0.90
            best = self.get_best_synonym(word, tag, self.sentence, candidates, threshold=current_threshold)
            output.append(best)
          else:
            output.append(word)

        result = ' '.join(output)
        for punct in [',', '.', '!', '?', ';', ':']:
            result = result.replace(f' {punct}', punct)
        return result
    except Exception as e:
        logger.error(f"Error in Synonym modification: {e}")
        return self.sentence
