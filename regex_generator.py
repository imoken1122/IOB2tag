import MeCab
import numpy as np
import re
import regex
# MeCabのインスタンスを作成
m = MeCab.Tagger()


class RegexGenerator():
    def __init__(self, attrValue: str, element_values: list, attrValue_pattern: str):
        self.tmp_attrValue = attrValue
        self.attrValue = attrValue
        self.element_values = element_values
        self.pattern = attrValue_pattern
        self.element_values_regex = []
        self.extracted_element_values = []
        self.tokens = self.preprocess(attrValue, self.element_values)
        self.tmp_tokens = self.tokens.copy()
        self.token_regex = self.convert_tokens_to_regex(self.tokens)


    # preprocess functions below



    def preprocess(self, attrValue, element_values):
        #element_valuesとそうではないものと分割
        tokens = self.split_attrValue_into_element_values(
            attrValue, element_values)
        #tokens = self.parse_non_elements(pretokens, element_values)
        return tokens


    def split_attrValue_into_element_values(self, text, element_values,):
        token = []
        start = 0
        for i, e_i in enumerate(element_values):
            end = text.find(e_i, start)
            if end == -1:
                break
            token.extend(self.parse_non_element(text[start:end]))
            token.append(e_i)
            start = end + len(e_i)
        token.extend(self.parse_non_element(text[start:]))
        return token
    
    def parse_non_element(self,token):
        if re.search("(\s|\n)", token) != None:

            parsed_token = sum([self.tokenizer(t) if t not in [" ", '\n'] else [
                t] for t in self.separate_meta_string(token)], [])
        else:
            parsed_token = self.tokenizer(token)
        return parsed_token
    
    def tokenizer(self, text):
        result = m.parse(text)
        # 分かち書き結果を分割
        tokens = result.split('\n')[:-2]
        tokens = [token.split('\t')[0] for token in tokens]
        return tokens

    def separate_meta_string(self, string):
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

    def parse_non_elements(self, token, element_values):
        result = []

        for i in range(len(token)):
            if token[i] not in element_values:
                if re.search("(\s|\n)", token[i]) != None:

                    parsed_token = sum([self.tokenizer(t) if t not in [" ", '\n'] else [
                        t] for t in self.separate_meta_string(token[i])], [])
                else:
                    parsed_token = self.tokenizer(token[i])

            else:
                parsed_token = [token[i]]

            result += parsed_token
        return result

    def is_contained_attrValuepattern(self, text):
        if self.pattern.find(text) != -1:
            return True
        else:
            return False

    def get_metastring_or_token(self, token):
        return re.escape(token) if re.search("(\s|\n)", token) == None else token.replace(' ', '\s')

    def get_prefix_and_suffix(self, idx):
        prefix, suffix = '', ''
        if idx != 0:

            prefix = self.get_metastring_or_token(self.tokens[idx-1])

            if not self.is_contained_attrValuepattern(prefix):
                if re.search('\\d', prefix[-1]):
                    prefix = '[\d\./]+'

                elif self.tokens[idx-2] == '\\':
                    prefix = ''.join(self.tokens[idx-2:idx])
                elif not re.search('\D', prefix[-1]) is None:
                    prefix = '\D+?'

        else:
            prefix = '^'

        if idx != len(self.tokens)-1:
            suffix = self.get_metastring_or_token(self.tokens[idx+1])
            suffix = self.extract_element('(^[A-Za-z]+)',suffix) if re.search('(^[A-Za-z]+)',suffix) and  suffix in self.element_values else suffix
            if not self.is_contained_attrValuepattern(suffix):
                if re.search('\\d', suffix[0]):
                    suffix = '\d'

                elif re.search('\D', suffix[0]):
                    suffix = '\D'

        else:
            suffix = '$'

        return prefix, suffix

    def get_capture_regex(self, token):
        if re.search('\n', token):
            return '(' + re.sub('[^\n]+','.+?',token) + ')'
        elif re.search('^\d+(?:，?[\./]\d+)?$', token):
            return '(\d+(?:[\./]\d+)?)'
        elif regex.search('^\d+(?:[\./]\d+)?[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+$', token):
            return '(\d.*?)'
        elif re.search('^[A-Z]+\d+(?:[\./]\d+)?$', token):
            return '([A-Za-z]+\d+(?:[\./]\d+)?)'
        elif regex.search('^[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+$', token):
            return '(\D+?)'
        else:
            return '(.+?)'

    def is_existed_regex(self, gen_regex):
        if gen_regex in self.element_values_regex:
            return True
        else:
            return False


    def extract_element(self, gen_regex, attrValue, verbose=False):
        try:
            extracted_element = regex.findall(gen_regex,attrValue)[0]
            return extracted_element
        except:
            if verbose:
                print('E : Syntax invalid regular expression provided. -> ', gen_regex)
            return ""



    def concat_ever_token_regex(self,ever_regex,gen_regex):

        return '^' + "".join(ever_regex[:]) + gen_regex
    
    def is_incorrect_generated_regex(self,element,gen_regex):

        return self.is_existed_regex(gen_regex) \
                or (
                    element != self.extract_element(gen_regex, self.tmp_attrValue) 
                    or element != self.extract_element( gen_regex,self.attrValue)
                ) 

    def generate_regex(self, element):

        idx = self.tmp_tokens.index(element)
        prefix, suffix = self.get_prefix_and_suffix(idx)
        cap_reg = self.get_capture_regex(element)
        gen_regex = prefix + cap_reg + suffix
        if self.is_incorrect_generated_regex(element,gen_regex):
            gen_regex = self.concat_ever_token_regex(self.token_regex[:idx-1],gen_regex)
        gen_regex =  self.try_regex_minimize(gen_regex, element, prefix + cap_reg + suffix, prefix, suffix, idx)
        self.tmp_tokens[idx] = '!'
        self.tmp_attrValue = re.sub(element,'!',self.tmp_attrValue,1)
        return gen_regex

    def excute(self):
        for q in self.element_values:
            gen_regex = self.generate_regex(q)
            output = gen_regex

            try:
               # print(r'{0}'.format(output), '\t',re.findall(output, self.attrValue)[0])
                self.extracted_element_values.append(
                    re.findall(output, self.attrValue)[0])
                self.element_values_regex.append(gen_regex)
            except:
                #print(output)
                self.extracted_element_values.append('')
                self.element_values_regex.append('')

    def convert_tokens_to_regex(self,tokens):
        
        token_regex =[]
        for i in range(len(tokens)):

            token = tokens[i]

            token = self.get_metastring_or_token(token)
            if self.is_contained_attrValuepattern(token):
                token_regex.append(token)
            elif re.search('\n', token):
                token_regex.append('[\s\S]+?')
            else: #token_regex[-1][-1] != '?':
                token_regex.append('.+?')

        return token_regex


            

    def try_regex_minimize(self, gen_regex, element, cap_reg, prefix, suffix, idx):

        def capture_replace(gen_regex,element):
            new_gen_regex = gen_regex.replace('\d+(?:[\./]\d+)?', '.+?').replace(
                '(\D+?)', '(.+?)').replace('\d.*?', '.+?').replace('[A-Za-z]+\d+(?:[\./]\d+)?', '.+?')
            return new_gen_regex if not self.is_incorrect_generated_regex(element,new_gen_regex) else gen_regex

        # キャプチャする正規表現から１つずつ前に遡り、element_valueと同じものがとれる正規表現はあるか走査する。
        new_gen_regex = gen_regex
        idx = gen_regex.find(cap_reg)
        for i in reversed(range(0, idx)):
            tmp_gen_regex = gen_regex[i:]
           
            try:
                if not self.is_incorrect_generated_regex(element,tmp_gen_regex):
                    new_gen_regex = tmp_gen_regex
                    break
            except:
                continue

        new_gen_regex = capture_replace(new_gen_regex, element)
        return new_gen_regex
