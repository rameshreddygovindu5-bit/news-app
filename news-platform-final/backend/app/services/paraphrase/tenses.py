import nltk
import string
import logging
from spacy.symbols import NOUN
from spacy.matcher import Matcher
import spacy

logger = logging.getLogger(__name__)

# Try internal pattern if available or fallback
try:
    from pattern3.en import conjugate, PAST, PRESENT, SINGULAR, PLURAL
except ImportError:
    # Minimal fallback for demonstration if pattern3 is missing
    PAST, PRESENT, SINGULAR, PLURAL = "past", "present", 1, 1
    def conjugate(word, **kwargs): return word

# Ensure NLTK and Spacy resources are available
for res in ['punkt', 'averaged_perceptron_tagger']:
    try:
        nltk.data.find(f'tokenizers/punkt' if res == 'punkt' else f'taggers/averaged_perceptron_tagger')
    except LookupError:
        nltk.download(res, quiet=True)

try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    nlp = None

class Tense():
    def __init__(self, input_sent, para):
        self.input_sent = input_sent
        self.para = para
        self.SUBJ_DEPS = {'agent', 'csubj', 'csubjpass', 'expl', 'nsubj', 'nsubjpass'}

    def identify_tense(self, text):
        if not nlp: return []
        doc = nlp(text)
        sents = list(doc.sents)
        print_table = []
        
        for sen in sents:
            doc_sen = nlp(str(sen))
            tense = 'Unknown'
            span = None
            
            # Simplified matching for demonstration
            # FUTURE
            matcher = Matcher(nlp.vocab)
            matcher.add('Future', None, [{'DEP':'nsubj'}, {'LOWER' : {'IN': ['will', 'shall']}}])
            matches = matcher(doc_sen)
            if matches:
                tense = 'Future'
                span = doc_sen[matches[0][1]:matches[0][2]]
            else:
                # PAST
                matcher = Matcher(nlp.vocab)
                matcher.add('Past', None, [{'DEP':'nsubj'}, {'TAG':'VBD'}])
                matches = matcher(doc_sen)
                if matches:
                    tense = 'Past'
                    span = doc_sen[matches[0][1]:matches[0][2]]
                else:
                    # PRESENT
                    matcher = Matcher(nlp.vocab)
                    matcher.add('Present', None, [{'DEP':'nsubj'}, {'TAG': {'IN': ['VBZ', 'VBP']}}])
                    matches = matcher(doc_sen)
                    if matches:
                        tense = 'Present'
                        span = doc_sen[matches[0][1]:matches[0][2]]

            print_table.append([sen, tense, span])
        return print_table

    def _get_conjuncts(self, tok):
        return [right for right in tok.rights if right.dep_ == 'conj']

    def is_plural_noun(self, token):
        return True if token.pos == NOUN and token.lemma != token.lower else False

    def get_subjects_of_verb(self, verb):
        if verb.dep_ == "aux" and list(verb.ancestors):
            return self.get_subjects_of_verb(list(verb.ancestors)[0])
        subjs = [tok for tok in verb.lefts if tok.dep_ in self.SUBJ_DEPS]
        subjs.extend(tok for subj in subjs for tok in self._get_conjuncts(subj))
        if not subjs:
            ancestors = list(verb.ancestors)
            if ancestors:
                return self.get_subjects_of_verb(ancestors[0])
        return subjs

    def is_plural_verb(self, token):
        subjects = self.get_subjects_of_verb(token)
        if not subjects:
            return False
        plural_score = sum([self.is_plural_noun(x) for x in subjects]) / len(subjects)
        return plural_score > .5

    def preserve_caps(self, word, newWord):
        if word and word[0].isupper():
            newWord = newWord.capitalize()
        return newWord

    def change_tense(self, text, to_tense):
        if not nlp: return text
        tense_lookup = {'future': 'inf', 'present': PRESENT, 'past': PAST}
        target_tense = tense_lookup.get(to_tense.lower(), PRESENT)

        doc = nlp(text)
        out = []
        words = list(doc)
        
        for i, word in enumerate(words):
            if i == 0:
                out.append(word.text)
                continue

            prev_word = words[i-1]
            if word.pos_ == 'VERB' and word.tag_ in ('VBD', 'VBP', 'VBZ', 'VBN', 'VB'):
                subjects = [x.text for x in self.get_subjects_of_verb(word)]
                person = 1 if any(s.lower() in ['i', 'we'] for s in subjects) else (2 if 'you' in [s.lower() for s in subjects] else 3)
                number = PLURAL if self.is_plural_verb(word) else SINGULAR
                
                try:
                    conjugated_word = conjugate(word.text, tense=target_tense, person=person, number=number)
                    out.append(self.preserve_caps(word.text, conjugated_word if conjugated_word else word.text))
                except:
                    out.append(word.text)
            else:
                out.append(word.text)

        text_out = ' '.join(out)
        for char in string.punctuation:
            text_out = text_out.replace(' ' + char, char)
        return text_out

    def main(self):
        if not self.para or not self.input_sent: return self.para
        try:
            tense1_info = self.identify_tense(self.input_sent)
            tense2_info = self.identify_tense(self.para)
            
            if not tense1_info or not tense2_info:
                return self.para
            
            tense1 = tense1_info[0][1]
            tense2 = tense2_info[0][1]
            
            if tense1 != tense2 and tense1 != 'Unknown':
                to_tense = tense1.lower()
                return self.change_tense(self.para, to_tense)
        except Exception as e:
            logger.error(f"Error in Tense rectification: {e}")
        return self.para
