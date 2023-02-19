import MeCab
import numpy as np
import re
import regex
# MeCabのインスタンスを作成
m = MeCab.Tagger()


class RegexGenerator():
    def __init__(self, attrValue, phrases, attrValue_pattern):
        self.attrValue = attrValue
        self.query = phrases
        self.pattern = attrValue_pattern
        self.ever_regex = '^'
        self.query_regex = []
        self.pre_idx = 0
        self.extracted_elements = []
        self.pretokens = self.phrase_split(attrValue, phrases)
        self.tokens = self.subtoken_split(self.pretokens, phrases)

    # preprocess functions below

    def phrase_split(self, text, phrases,):
        token = []
        start = 0
        for i, phrase in enumerate(phrases):
            end = text.find(phrase, start)
            if end == -1:
                break
            token.append(text[start:end])
            token.append(phrase)
            start = end + len(phrase)
        token.append(text[start:])
        return token

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

    def subtoken_split(self, token, phrases):
        result = []

        for i in range(len(token)):
            if token[i] not in phrases:
                if re.search("(\s|\n)", token[i]) != None:

                    subtoken = sum([self.tokenizer(t) if t not in [" ", '\n'] else [
                                   t] for t in self.separate_meta_string(token[i])], [])
                else:
                    subtoken = self.tokenizer(token[i])

            else:
                subtoken = [token[i]]

            result += subtoken
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
                    prefix = '\d'

                elif self.tokens[idx-2] == '\\':
                    prefix = ''.join(self.tokens[idx-2:idx])
               # elif not re.search('\D', prefix[-1]) is None:
               #     prefix = '\D'
                else:
                    # prefix = '[\\p{Script=Han}]\\p{Script=Katakana}\\p{Script=Hiragana}A-Za-zー]'
                    prefix = '.+?'

        else:
            prefix = '^'

        if idx != len(self.tokens)-1:
            suffix = self.get_metastring_or_token(self.tokens[idx+1])

            if not self.is_contained_attrValuepattern(suffix):
                if re.search('\\d', suffix[0]):
                    suffix = '\d'

                elif re.search('\D', suffix[0]):
                    suffix = '\D'
                else:
                    # suffix = '[\\p{Script=Han}\\p{Script=Katakana}\\p{Script=Hiragana}A-Za-zー]'
                    suffix = '.+?'

        else:
            suffix = '$'

        return prefix, suffix

    def get_capture_regex(self, token):
        if re.search('^\d(?:[\./]?\d+)?$', token):
            return '(\d(?:[\./]?\d+)?)'
        elif regex.search('^[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+$', token):
            return '(\D+?)'
        else:
            return '(.+?)'

    def is_existed_regex(self, gen_regex):
        if gen_regex in self.query_regex:
            return True
        else:
            return False

    def is_correct_extract_element(self, query, gen_regex):

        extract_element = regex.findall(gen_regex, self.attrValue)[0]
        if extract_element == query:
            return True
        else:
            return False

    def try_fix_regex(self, gen_regex, prefix, suffix):

        if self.ever_regex[-2] == '\\':
            er = self.ever_regex[:-2]
        elif prefix == '.+?' and self.ever_regex[-1] == '?':
            er = self.ever_regex[:-3]
        elif self.ever_regex[-1] == '?':
            er = self.ever_regex
        else:
            er = self.ever_regex[:-1]
        gen_regex = er + gen_regex

        return gen_regex

    def generate_regex(self, query):

        idx = self.tokens[self.pre_idx:].index(query) + self.pre_idx

        prefix, suffix = self.get_prefix_and_suffix(idx)

        cap_reg = self.get_capture_regex(self.tokens[idx])
        gen_regex = prefix + cap_reg + suffix

        self.save_ever_regex(idx)

        if self.is_existed_regex(gen_regex) or not self.is_correct_extract_element(query, gen_regex):
            gen_regex = self.try_fix_regex(gen_regex, prefix, suffix)

        self.query_regex.append(gen_regex)

        self.pre_idx = idx

        return self.try_regex_minimize(gen_regex, query, prefix, suffix, idx)

    def excute(self):
        for q in self.query:
            gen_regex = self.generate_regex(q)
            output = gen_regex

            try:
                print(r'{0}'.format(output), '\t', re.findall(output, self.attrValue)[0])
                self.extracted_elements.append(re.findall(output, self.attrValue)[0])
            except:
                print(output)
                self.extracted_elements.append('')
    def save_ever_regex(self, idx):

        for i in range(self.pre_idx, idx):
            token = self.tokens[i]

            token = self.get_metastring_or_token(token)
            if self.is_contained_attrValuepattern(token):
                self.ever_regex += token
            elif self.ever_regex[-1] != '?':
                self.ever_regex += '.+?'
            else:
                continue

    def try_regex_minimize(self, gen_regex, query, prefix, suffix, idx):
        if len(gen_regex) <= 8:  # 生成される正規表現の長さは最小で lenght=8
            return gen_regex

        if self.is_contained_attrValuepattern(prefix) and self.is_contained_attrValuepattern(suffix):
            new_gen_regex = gen_regex.replace('\d(?:[\./]?\d+)?','.+?').replace('\D+?','.+?')
            if self.is_correct_extract_element(query,new_gen_regex):
                gen_regex = new_gen_regex
            
            # 何らかの処理で正規表現を短くする

            """   
            tmp_ever_regex =self.ever_regex.replace('.+?','').replace('\\','') #patternに含まれる限定した文字のみ
            tmp,tmp1 = '',''
            regex_list = []
            for i in reversed(range(len(tmp_ever_regex))):
                tmp = '.*' + re.escape(tmp_ever_regex[i] ).replace('s','\s').replace('\\\n','\n')
                tmp1 = tmp + tmp1
                new_regex = tmp1 + gen_regex
                print(new_regex)
                if self.is_correct_extract_element(query, new_regex):
                    regex_list.append(new_regex)
            """
        return gen_regex


'''
S = 'サイズ/Rc1/8、100cm、(方法/ねじ込み)空気、別尺ー・：100mm'
pattern = 'サイズ/[A-Z]+\d/\d、\d+cm、\([\p{Han}\p{Katakana}\p{Hiragana}ー]+/[\p{Han}\p{Katakana}\p{Hiragana}ー]+\)[\p{Han}\p{Katakana}\p{Hiragana}ー]+、[\p{Han}\p{Katakana}\p{Hiragana}ー]+・：\d+mm'
querys = ["Rc", "1/8", '100', '方法/ねじ込み', '空気', '100']
instance =RegexGenerator(S,querys,pattern)
instance.excute()
'''