import torch
import torch.nn as nn

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

def one_hot(phrase, c):
    return torch.zeros(*phrase.size(), c, device=device).scatter_(-1, phrase.unsqueeze(-1), 1)

class Encoder(nn.Module):
    def __init__(self, opt):
        super(Encoder,self).__init__()
        self.max_seq_len = opt["max_seq_len"]
        self.vocab_sz = opt["vocab_sz"]
        self.emb_layer = nn.Sequential(
            nn.Linear(opt["vocab_sz"], opt["emb_hid_dim"]),
            nn.Threshold(0.000001, 0),
            nn.Dropout(opt['enc_dropout']),
            nn.Linear(opt['emb_hid_dim'], opt['emb_dim']),
            nn.Threshold(0.000001, 0))
        self.enc_rnn = nn.GRU(opt['emb_dim'], opt['enc_rnn_dim'])
        self.enc_lin = nn.Sequential(
            nn.Dropout(opt['enc_dropout']),
            nn.Linear(opt['enc_rnn_dim'], opt['enc_dim']))

    def forward(self, phrase):
        emb = self.emb_layer(one_hot(phrase, self.vocab_sz))
        enc_out_rnn = self.enc_rnn(emb)[1]
        enc_phrase = self.enc_lin(enc_out_rnn)
        return enc_phrase
