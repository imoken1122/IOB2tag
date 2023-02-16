import MeCab
import numpy as np
import re
# MeCabのインスタンスを作成
m = MeCab.Tagger()



class Regex_Generator():
    def __init__(self,attrValue,phrases,attrValue_pattern):
        self.attrValue = attrValue

        self.pattern = attrValue_pattern
        self.ever_regex = '^'
        self.query_regex = []
        self.pre_idx = 0
        self.meta_str = ['\\',' ']
        self.pretokens =  self.phrase_split(attrValue,phrases)
        self.tokens  =  self.subtoken_split(self.pretokens,phrases)
    def is_contained_attrValuepattern(self,text):
        if not re.search(text, self.pattern) is None:
            return True
        else:
            return False
    def get_prefix_and_suffix(self,toknes,idx,pattern):
        prefix,suffix ='','' 
        if idx !=0:
            prefix = re.escape(self.tokens[idx-1]) if self.tokens[idx-1] not in self.meta_str else self.tokens[idx-1]
            if not self.is_contained_attrValuepattern(prefix):
                if not re.search('\\d', prefix[-1]) is None:
                    prefix = '\d'
                elif not re.search('(\n|\s)',prefix[-1]) is None:
                    prefix = '\s'
                elif self.tokens[idx-2] == '\\':
                    prefix = ''.join(self.tokens[idx-2:idx])
                else:
                    #prefix = '[\\p{Script=Han}]\\p{Script=Katakana}\\p{Script=Hiragana}A-Za-zー]'
                    prefix = '.+?'

        else:
            prefix = '^'

        if idx != len(self.tokens)-1:
            suffix = re.escape(self.tokens[idx+1]) if self.tokens[idx+1] not in self.meta_str else self.tokens[idx+1]
            if not self.is_contained_attrValuepattern(suffix):
                if not re.search('\\d', suffix[0]) is None:
                    suffix = '\d'
                elif not re.search('\s',suffix[0]) is None:
                    suffix = '\s'
                elif  suffix[0] == '\\':

                    suffix = ''.join(self.tokens[idx+1:idx+4])
                else:
                    #suffix = '[\\p{Script=Han}]\\p{Script=Katakana}\\p{Script=Hiragana}A-Za-zー]'
                    suffix = '.+?'

        else:
            suffix = '$'

        return prefix,suffix
    def get_capture_regex(self,token):
        if re.search('^\d(?:[\./]?\d+)?$',token):
            return '(\d(?:[\./]?\d+)?)'
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

        idx  =self.tokens[self.pre_idx:].index(query)+ self.pre_idx

        prefix,suffix = self.get_prefix_and_suffix(self.tokens,idx,self.pattern)

        cap_reg = self.get_capture_regex(self.tokens[idx])
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
            
            if self.is_contained_attrValuepattern(token.replace(' ','\s')):
                self.ever_regex += re.escape(token) if  re.search("(\s|\n)" ,token) == None else token.replace(' ','\s')
                
            else:
                self.ever_regex += '.+?'

## preprocess functions below

    def phrase_split(self,text,phrases,):
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


    def tokenizer(self,text):
        result = m.parse(text)
        # 分かち書き結果を分割
        tokens = result.split('\n')[:-2]
        tokens = [token.split('\t')[0] for token in tokens]
        return tokens

    def separate_meta_string(self,string):
        result = []
        temp = ""
        for c in string:
            if c in [" ", "\n"]:
                # 空白・改行が出現した場合
                if temp != "":
                    result.append(temp)
                result.append(c)
                temp = ""
            else:
                temp += c
        if temp != "":
            result.append(temp)
        return result


    def subtoken_split(self,token,phrases):
        result = []

        for i in range(len(token)):
            if token[i] not in phrases: 
                if re.search("(\s|\n)",token[i]) != None:
                    
                    subtoken = sum([ self.tokenizer(t) if t not in [" ",'\n'] else [t] for t in self.separate_meta_string(token[i])],[])
                else:
                    subtoken = self.tokenizer(token[i])

            else:
                subtoken =  [token[i]]

            result += subtoken
        return result


S = '【ねじ込み】238 、56(折りたたみ)、98(常時)\n2348 (非常時 )mm'
query = ['ねじ込み','238','56','折りたたみ','98','常時','2348','非常時']
pattern = '【[\p{Han}+]】\d+\s、\d+\([\p{Han}+]\)、\d+\([\p{Han}+]\)\n\d+\s\(\p{Han}+\s\)mm'

rg = Regex_Generator(S,query, pattern)
for q in query:
    gen_regex = rg.generate_regex(q)
    output = gen_regex
#    result[result.index(q)] = ''

    try:
        print(r'{0}'.format(output),'\t',re.findall(output,S)[0])
    except:
        print(output)