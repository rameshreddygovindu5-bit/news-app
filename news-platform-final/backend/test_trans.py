
from googletrans import Translator

translator = Translator()
try:
    result = translator.translate("Hello world", dest='te')
    print("Translated:", result.text)
except Exception as e:
    print("Error:", e)
