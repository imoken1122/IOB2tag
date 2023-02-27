import MeCab
import numpy as np
import re
import regex
# MeCabのインスタンスを作成
m = MeCab.Tagger()


class RegexGenerator():
    def __init__(self, attrValue: str, element_values: list, attrValue_pattern: str):
        self.attrValue = attrValue
        self.element_values = element_values
        self.pattern = attrValue_pattern
        self.ever_regex = '^'
        self.element_values_regex = []
        self.next_idx = 0
        self.extracted_element_values = []
        self.tokens = self.preprocess(attrValue, element_values)

    # preprocess functions below
    def preprocess(self, attrValue, element_values):
        pretokens = self.split_attrValue_into_element_values(
            attrValue, element_values)
        tokens = self.parse_non_elements(pretokens, element_values)
        return tokens

    def split_attrValue_into_element_values(self, text, element_values,):
        token = []
        start = 0
        for i, e_i in enumerate(element_values):
            end = text.find(e_i, start)
            if end == -1:
                break
            token.append(text[start:end])
            token.append(e_i)
            start = end + len(e_i)
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
                    prefix = '\d'

                elif self.tokens[idx-2] == '\\':
                    prefix = ''.join(self.tokens[idx-2:idx])
                elif not re.search('\D', prefix[-1]) is None:
                    prefix = '\D+?'
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
        if re.search('\n', token):
            return '([\s\S]+?)'
        elif re.search('^\d+(?:[\./]\d+)?$', token):
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

    def is_correct_extract_element(self, element, gen_regex):
        try:
            extract_element = regex.findall(gen_regex, self.attrValue)[0]
            if extract_element == element:
                return True
            else:
                return False
        except:
            print('E : Syntax invalid regular expression provided. -> ',
                  self.attrValue, element, gen_regex)
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

    def generate_regex(self, element):
        idx = self.tokens.index(element, self.next_idx)
        prefix, suffix = self.get_prefix_and_suffix(idx)
        cap_reg = self.get_capture_regex(element)
        gen_regex = prefix + cap_reg + suffix
        self.save_ever_regex(max(self.next_idx-1, 0), max(idx, 1))
        if self.is_existed_regex(gen_regex) or not self.is_correct_extract_element(element, gen_regex):
            gen_regex = self.try_fix_regex(gen_regex, prefix, suffix)
        self.element_values_regex.append(gen_regex)
        self.next_idx = idx + 1
        return self.try_regex_minimize(gen_regex, element, prefix + cap_reg + suffix, prefix, suffix, idx)

    def excute(self):
        print(self.tokens)
        for q in self.element_values:
            gen_regex = self.generate_regex(q)
            output = gen_regex

            try:
                print(r'{0}'.format(output), '\t',
                      re.findall(output, self.attrValue)[0])
                self.extracted_element_values.append(
                    re.findall(output, self.attrValue)[0])
            except:
                print(output)
                self.extracted_element_values.append('')

    def save_ever_regex(self,next_idx ,idx):
        
        for i in range(next_idx, idx):

            token = self.tokens[i]

            token = self.get_metastring_or_token(token)
            if self.is_contained_attrValuepattern(token):
                self.ever_regex += token
            elif re.search('\n', token):
                self.ever_regex += '[\s\S]+?'
            elif self.ever_regex[-1] != '?':
                self.ever_regex += '.+?'
            else:
                continue

    def try_regex_minimize(self, gen_regex, element, cap_reg, prefix, suffix, idx):

        if self.is_contained_attrValuepattern(prefix) and self.is_contained_attrValuepattern(suffix):

            # キャプチャする正規表現から１つずつ前に遡り、element_valuesと同じものがとれる正規表現はあるか走査する。
            new_gen_regex = gen_regex
            idx = gen_regex.find(cap_reg)
            for i in reversed(range(0, idx)):
                new_gen_regex = gen_regex[i:]

                try:
                    extracted = re.findall(new_gen_regex, self.attrValue)[0]
                    if extracted == element:
                        break
                except:
                    continue

            new_gen_regex = new_gen_regex.replace('\d+(?:[\./]\d+)?', '.+?').replace(
                '\D+?', '.+?').replace('\d.*?', '.+?').replace('[A-Za-z]+\d+(?:[\./]\d+)?', '.+?')
            if self.is_correct_extract_element(element, new_gen_regex):
                gen_regex = new_gen_regex
        return gen_regex
