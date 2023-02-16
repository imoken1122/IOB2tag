import MeCab
import re
from typing import Dict, List, Tuple

# MeCabのインスタンスを作成
m = MeCab.Tagger()



class Regex_Generator():
    def __init__(self,attrValue: str,phrases: List[str],attrValue_pattern: str) -> None:
        self.attrValue = attrValue

        self.pattern = attrValue_pattern
        self.ever_regex = '^'
        self.query_regex = []
        self.pre_idx = 0
        self.meta_str = ['\\',' ']
        self.pretokens =  self.phrase_split(attrValue,phrases)
        self.tokens  =  self.subtoken_split(self.pretokens,phrases)
    def is_contained_attrValuepattern(self, text: str) -> bool:
        if not re.search(text, self.pattern) is None:
            return True
        else:
            return False
    def get_prefix_and_suffix(self,tokens:List[str],idx:int)->Tuple[str,str]:
        prefix,suffix ='','' 
        if idx !=0:
            prefix = ''
            if not self.is_contained_attrValuepattern(prefix):
                if not re.search('\\d', prefix[-1]) is None:
                    prefix = '\d'
                elif not re.search('(\n|\s)',prefix[-1]) is None:
                    prefix = '\s'
                elif tokens[idx-2] == '\\':
                    prefix = ''.join(tokens[idx-2:idx])
                else:
                    prefix = re.escape(tokens[idx-1]) if tokens[idx-1] not in self.meta_str else tokens[idx-1]
        else:
            prefix = '^'

        if idx != len(tokens)-1:
            suffix =  ''
            if not self.is_contained_attrValuepattern(suffix):
                if not re.search('\\d', suffix[0]) is None:
                    suffix = '\d'
                elif not re.search('\s',suffix[0]) is None:
                    suffix = '\s'
                elif  suffix[0] == '\\':

                    suffix = ''.join(tokens[idx+1:idx+4])
                else:
                    suffix = re.escape(tokens[idx+1]) if tokens[idx+1] not in self.meta_str else tokens[idx+1]
        else:
            suffix = '$'

        return prefix,suffix
    def get_capture_regex(self,token: str) -> str:
        if re.search('^\d(?:[\./]?\d+)?$',token):
            return '(\d(?:[\./]?\d+)?)'
        else:
            return '(.+?)'
    def is_existed_regex(self,gen_regex: str) -> bool:
        if gen_regex in self.query_regex:
            return True
        else:
            return False
    def is_correct_extract_element(self, query: str, gen_regex: str) -> bool:

            extract_element = re.findall(gen_regex,self.attrValue)[0]
            if extract_element == query:
                return True
            else:
                return False
            
    def generate_regex(self, query: str) -> str:

        idx  =self.tokens[self.pre_idx:].index(query)+ self.pre_idx

        prefix,suffix = self.get_prefix_and_suffix(self.tokens,idx)

        cap_reg = self.get_capture_regex(self.tokens[idx])
        gen_regex= prefix + cap_reg + suffix
        
        self.save_ever_regex(idx)

        if self.is_existed_regex(gen_regex) or not self.is_correct_extract_element(query,gen_regex):
            gen_regex = (self.ever_regex[:-2] if self.ever_regex[-2] == '\\' else self.ever_regex[:-1]) + gen_regex
        self.query_regex.append(gen_regex)

        self.pre_idx = idx
        return gen_regex

    def save_ever_regex(self, idx: int) -> None:
        
        for i in range(self.pre_idx,idx):
            token = self.tokens[i]
            
            if self.is_contained_attrValuepattern(token.replace(' ','\s')):
                self.ever_regex += re.escape(token) if  re.search("(\s|\n)" ,token) == None else token.replace(' ','\s')
                
            else:
                self.ever_regex += '.+?'

## preprocess functions below

    def phrase_split(self, text: str, phrases: List[str]) -> List[str]:
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


    def tokenizer(self,text:str) -> list:
        result = m.parse(text)
        # 分かち書き結果を分割
        tokens = result.split('\n')[:-2]
        tokens = [token.split('\t')[0] for token in tokens]
        return tokens

    def separate_meta_string(self,string: str) -> Tuple[str, str]:
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


    def subtoken_split(self,token: str,phrases: List[str]) -> List[str]:
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