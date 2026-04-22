import re
import logging
from .synonym import Synonym
from .antonym import Antonym
from .tenses import Tense

logger = logging.getLogger(__name__)

def local_paraphrase(original_sent, paraphrase_text=None):
    """
    The 'Local Paraphrase Engine' mirroring generate_paraphrase.py logic.
    If paraphrase_text is provided, it acts as a polisher.
    If only original_sent is provided, it rephrases it from scratch using local rules.
    """
    # 1. Initialization
    input_sent = original_sent
    # If no rephrased version exists, we start with the original
    current_text = paraphrase_text if paraphrase_text else original_sent

    try:
        # Step A: Proper Noun Segregation (from prepro_utils logic)
        # Note: For simple lexical modification, we often just work on the text
        # but to mirror the 'last stage' perfectly:
        
        # Step B: Lexical Mods (Synonym -> Antonym)
        syn = Synonym(current_text)
        current_text = syn.main()
        
        ant = Antonym(current_text)
        current_text = ant.main()
        
        # Step C: Tense Rectification (The actual 'Last Stage' requirement)
        ten = Tense(original_sent, current_text)
        current_text = ten.main()
        
        return current_text
    except Exception as e:
        logger.error(f"Local Paraphrase Engine failed: {e}")
        return current_text

def apply_lexical_modifications(original_sent, paraphrase_html):
    """
    Applies the full lexical modification pipeline while preserving HTML structure.
    Used for polishing AI output.
    """
    if not paraphrase_html:
        return paraphrase_html

    # Clean the original sentence of HTML for comparison/tense logic
    original_clean = re.sub(r'<[^>]+>', '', original_sent)

    try:
        # We split the HTML and only process the text parts
        parts = re.split(r'(<[^>]+>)', paraphrase_html)
        result = []
        for part in parts:
            if part.startswith('<'):
                result.append(part)
            elif part.strip():
                # Apply the full Local Paraphrase logic to the text chunk
                result.append(local_paraphrase(original_clean, part))
            else:
                result.append(part)
        
        return "".join(result)
    except Exception as e:
        logger.warning(f"HTML-aware lexical modification failed: {e}")
        return paraphrase_html
