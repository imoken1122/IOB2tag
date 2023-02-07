text = ["今日は陽気な一日です。明日も陽気ですように。"]
phrases = ["陽気な一日", "陽気ですように"]
text = 'サイズ/Rc1/8、100cm、(方法/ねじ込み)'

phrases = ["Rc","1/8",'100','方法/ねじ込み']
label = ['菅種類','呼び系','主体','補足']

import re
def phrase_split(text,phrases,):
    token = []
    start = 0
    for i,phrase in enumerate(phrases):
        end = text.find(phrase, start)
        if end == -1:
            break
        token.append(text[start:end])
        token.append(phrase)
        start = end + len(phrase)
    token.append(text[start:])
    return token

def identify_phrases(text,phrases,label):
    token = phrase_split(text,phrases)
    m = MeCab.Tagger()
    text_tags = []
    text_token = []
    for t in token:
        if t == '': continue
        parse = [ p.split('\t')[0] for p in m.parse(t).split('\n')][:-2]

        if t in phrases:

            label_idx = phrases.index(t)
            if re.search('\d+(\.?\/?\d+)?',t) != None and re.search('(対象|補足|条件)',label[label_idx]) == None:
                tag = '主体'
            elif re.search('(主体|対象|補足|条件)',label[label_idx]) != None:
                tag = label[label_idx]
            else:
                tag = 'その他'
        
            text_tags.extend([f"B-{tag}"] + [f"I-{tag}"]*(len(parse)-1))
            text_token.extend(parse)
        else:
            text_tags.extend(["O"]*len(parse))
            text_token.extend(parse)
    return text_tags

def containe_tag_tokenizer(text,phrases,label):
    
    text_tags = identify_phrases(text,phrases,label)
    m = MeCab.Tagger()
    parse = m.parse(text).split("\n")[:-2]
    #print(len(parse),len(text_tags))
    for i in range(len(parse)):
        parse[i] += '\t' + text_tags[i]+'\n'
        print(parse[i])
    return parse


