import torch
import torch.nn as nn

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

class Decoder(nn.Module):
    def __init__(self, opt):
        super(Decoder, self).__init__()
        self.max_seq_len = opt["max_seq_len"]
        self.vocab_sz = opt["vocab_sz"]
        self.dec_emb = nn.Embedding(opt['vocab_sz'], opt['emb_dim'])
        self.dec_rnn = nn.LSTM(opt['emb_dim'], opt['dec_rnn_dim'])
        self.dec_lin = nn.Sequential(
            nn.Dropout(opt['dec_dropout']),
            nn.Linear(opt['dec_rnn_dim'], opt['vocab_sz']),
            nn.LogSoftmax(dim =-1)
        )

    def forward(self, phrase, enc_phrase, similar_phrase = None, teacher_forcing = False):
        if similar_phrase == None:
            similar_phrase = phrase
        
        words = []
        h = None
        if not teacher_forcing:
            emb_sim_phrase_dec = self.dec_emb(similar_phrase)
            dec_rnn_inp = torch.cat([enc_phrase, emb_sim_phrase_dec[:-1, :]], dim=0) 
            out_rnn, _ = self.dec_rnn(dec_rnn_inp)
            out = self.dec_lin(out_rnn)
        else:
          for __ in range(self.max_seq_len):
              word, h = self.dec_rnn(enc_phrase, hx=h)
              word = self.dec_lin(word)
              words.append(word)
              word = torch.multinomial(torch.exp(word[0]), 1)
              word = word.t()
              enc_phrase = self.dec_emb(word)
          out = torch.cat(words, dim=0).to(device)
        return out
