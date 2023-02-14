class Regex_Generator():
    def __init__(self,attrValue, tokens,attrValue_pattern):
        self.attrValue = attrValue
        self.tokens  =tokens

        self.pattern = attrValue_pattern
        self.ever_regex = '^'
        self.query_regex = []
        self.pre_idx = 0
        
    def is_contained_attrValuepattern(self,text):
        if not re.search(re.escape(text), self.pattern) is None:
            return True
        else:
            return False
    def get_prefix_and_suffix(self,toknes,idx,pattern):
        prefix,suffix ='','' 
        if idx !=0:
            prefix = re.escape(result[idx-1])
            if not self.is_contained_attrValuepattern(prefix):
                if not re.search('\\d', prefix[-1]) is None:
                    prefix = '\d'
                else:
                    #prefix = '[\\p{Script=Han}]\\p{Script=Katakana}\\p{Script=Hiragana}A-Za-zー]'
                    prefix = '.+?'

        else:
            prefix = '^'

        if idx != len(result)-1:
            suffix = re.escape(result[idx+1])

            if not self.is_contained_attrValuepattern(suffix):
                if not re.search('\\d', suffix[0]) is None:
                    suffix = '\d'
                else:
                    #suffix = '[\\p{Script=Han}]\\p{Script=Katakana}\\p{Script=Hiragana}A-Za-zー]'
                    suffix = '.+?'

        else:
            suffix = '$'

        return prefix,suffix
    def get_capture_regex(self,token):
        if re.search('\d+(?:[\./]\d+)?',token):
            return '(\d+(?:[\./]\d+)?)'
        else:
            return '(.+?)'
    def is_existed_regex(self,gen_regex):
        if gen_regex in self.query_regex:
            return True
        else:
            return False
    def is_correct_extract_element(self,query ,gen_regex):
            extract_element = re.findall(gen_regex,self.attrValue)[0]
            if extract_element == query:
                return True
            else:
                return False
    def generate_regex(self, query):

        idx  =self.tokens[self.pre_idx:] .index(query)+ self.pre_idx

        prefix,suffix = get_prefix_and_suffix(self.tokens,idx,self.pattern)
        cap_reg = get_capture_regex(self.tokens[idx])
        gen_regex= prefix + cap_reg + suffix
        self.save_ever_regex(idx)

        if self.is_existed_regex(gen_regex) or not self.is_correct_extract_element(query,gen_regex):
            gen_regex = (self.ever_regex[:-2] if self.ever_regex[-2] == '\\' else self.ever_regex[:-1]) + gen_regex
        self.query_regex.append(gen_regex)

        self.pre_idx = idx      
        return gen_regex

    def save_ever_regex(self,idx):

        for i in range(self.pre_idx,idx):
            token = self.tokens[i]
            if self.is_contained_attrValuepattern(token):
                self.ever_regex += re.escape(token)
                
            else:
                self.ever_regex += '.+?'

                
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
def tokenizer(text):
    result = m.parse(text)
    # 分かち書き結果を分割
    tokens = result.split('\n')[:-2]
    tokens = [token.split('\t')[0] for token in tokens]
    return tokens
            
S = 'サイズ/Rc1/8、100cm、(方法/ねじ込み)空気、別尺ー・：100mm'
query = ["Rc","1/8",'100','方法/ねじ込み','空気','100']
pattern = 'サイズ/[A-Z]+\d/\d、\d+cm、\([\p{Han}\p{Katakana}\p{Hiragana}ー]+/[\p{Han}\p{Katakana}\p{Hiragana}ー]+\)[\p{Han}\p{Katakana}\p{Hiragana}ー]+、[\p{Han}\p{Katakana}\p{Hiragana}ー]+・：\d+mm'

S = '1×10×234×111×456×999'
query = ['1','10','234','111','456','999']
pattern = '\d+×\d+×\d+×\d+×\d+×\d+'


S = '【ねじ込み】238、56(折りたたみ)、98(常時),2348(非常時)mm'
query = ['ねじ込み','238','56','折りたたみ','常時','2348','非常時']
pattern = '【[\p{Han}+]】\d+、\d+\([\p{Han}+]\)、\d+\([\p{Han}+]\),\d+\([\p{Han}+]\)mm'
token = phrase_split(S,query)
result = []

for i in range(len(token)):
    if token[i] not in query: 
        subtoken = tokenizer(token[i])

    else:
        subtoken =  [token[i]]

    result += subtoken

save_regex = []
rg = Regex_Generator(S,result, pattern)
for q in query:
    gen_regex = rg.generate_regex(q)
    output = gen_regex
#    result[result.index(q)] = ''

    try:
        print(output,'\t',re.findall(output,S)[0])
    except:
        print(output)

    
        

