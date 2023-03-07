from typing import Final

import MeCab
import re,regex
m = MeCab.Tagger()

class element_RegexGenerator:
    def __init__(self,attrValue:str, element_values: str, attrValue_pattern:str):
        self.meta_str = r'( |\n)'
        self.attrValue = attrValue
        self.element_values = element_values
        self.attrValue_pattern = attrValue_pattern
        self.element_id_values = self.assign_id_element_values(element_values)
        self.attrValue_id = self.assign_id_attrValue(attrValue,self.element_id_values)

        self.attrValue_tokens = self.parse_attrValue(self.attrValue_id, self.element_id_values)
        self.token_regex = self.convert_tokens_to_regex(self.attrValue_tokens)

    
        self.element_patterns = []
        self.extracted_element_values = []
        print(self.attrValue_id)


    def assign_id_attrValue(self,attrValue:str,element_id_values:list) -> str:
        idx = 0
        attrValue_id = ''
        for elm_id in element_id_values:
            remove_id_elm = re.sub('_id.*','',elm_id)
            elm_idx = attrValue.find(remove_id_elm, idx)
            if elm_idx == -1:break
            attrValue_id += attrValue[idx:elm_idx]
            attrValue_id += elm_id
            idx = elm_idx+len(remove_id_elm)
        attrValue_id += attrValue[idx:]
        return attrValue_id

    def assign_id_element_values(self,element_values:list) -> list:

        # 各要素に一意のIDを割り当てるための辞書を作成する
        id_dict = {}
        new_list = []
        for elem in element_values:
            if elem not in id_dict.keys():
                id_dict[elem] = 0
            new_list.append(elem + f'_id_{id_dict[elem]}')
            id_dict[elem] += 1


        return new_list
    
    # attrValue を token に分解する
    def parse_attrValue(self, attrValue:str, element_values:list) -> list:
        token = []
        start = 0
        for i, e_i in enumerate(element_values):
            end = attrValue.find(e_i, start)
            if end == -1:
                break
            # parse_non_element で最小単位まで分解
            token.extend(self.parse_non_element(attrValue[start:end]))
            # element_values は分解しない
            token.append(e_i)
            start = end + len(e_i)
        token.extend(self.parse_non_element(attrValue[start:]))
        return token
    
    def parse_non_element(self,token):
        if re.search("(\s|\n)", token) != None:

            parsed_token = sum([self.tokenizer(t) if not re.search(self.meta_str,t) 
                                else [t] 
                                for t in self.parse_meta_string(token)], [])
        else:
            parsed_token = self.tokenizer(token)
        return parsed_token
    
    def parse_meta_string(self,token):
        return [t for t in re.split(self.meta_str, token) if t !='']
    

    def tokenizer(self, text):
        result = m.parse(text)
        # 分かち書き結果を分割
        tokens = result.split('\n')[:-2]
        tokens = [token.split('\t')[0] for token in tokens]
        return tokens
    
    def escape_token(self, token):
        return re.escape(token) if re.search("(\s|\n)", token) == None else token.replace(' ', '\s')

    def convert_tokens_to_regex(self,tokens):
        
        token_regex =[]
        for i in range(len(tokens)):

            token = tokens[i]

            token = self.escape_token(token)
            if self.is_contained_attrValue_pattern(token):
                token_regex.append(token)
            elif re.search('\n', token):
                token_regex.append('[\s\S]+?')
            else:
                token_regex.append('.+?')

        return token_regex

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
        
    def is_contained_attrValue_pattern(self, text):
        if self.attrValue_pattern.find(text) != -1:
            return True
        else:
            return False
    def get_prefix_and_suffix(self,tokens ,idx, ):
        prefix, suffix = '', ''
        if idx != 0:

            prefix = self.escape_token(tokens[idx-1])
            prefix = self.remove_id(prefix)

            if not self.is_contained_attrValue_pattern(prefix):
                if re.search('\\d', prefix[-1]):
                    prefix = '[\d\./]+'

                elif tokens[idx-2] == '\\':
                    prefix = ''.join(tokens[idx-2:idx])
                elif not re.search('\D', prefix[-1]) is None:
                    prefix = '\D+?'

        else:
            prefix = '^'

        if idx != len(tokens)-1:
            suffix = self.escape_token(tokens[idx+1])
            suffix = self.extract_element('(^[A-Za-z]+)',suffix) if re.search('(^[A-Za-z]+)',suffix) and  suffix in self.element_id_values else suffix
            if not self.is_contained_attrValue_pattern(suffix):
                if re.search('\\d', suffix[0]):
                    suffix = '\d'

                elif re.search('\D', suffix[0]):
                    suffix = '\D'

        else:
            suffix = '$'

        return prefix, suffix

    def extract_element(self,gen_regex,attrValue,verbose=False):
        try:
            extracted_element = re.findall(gen_regex, attrValue)[0]
        except:
            if verbose:
                print('E : Syntax invalid regular expression provided. -> ', gen_regex)
            extracted_element = ''
        return extracted_element


    def is_correct_generated_regex(self,gen_regex,element):
        print(gen_regex)
        try:
            extracted_element = self.extract_element(gen_regex,self.attrValue_id)
        except:
            extracted_element = ''
        print(extracted_element)
        if extracted_element == element :
            return True

        else:
            return False
    
    def concat_ever_token_regex(self,ever_regex,gen_regex):
        return '^' + "".join(ever_regex[:]) + gen_regex

    def remove_id(self,token):
        return  re.sub('_id_\d+','',token) 
    def get_id(self,token):
        return self.extract_element('_id_(\d+)',token)
    def append_id(self,token,id):
        return token[:-1] + f'_id_{id})'

    def generate_element_pattern(self,element_id_value:str):

        elem_idx = self.attrValue_tokens.index(element_id_value)
        # element の idを取り除いてキャプチャするregexを決める
        element = self.remove_id(element_id_value)
        elem_id = self.get_id(element_id_value)
        prefix, suffix = self.get_prefix_and_suffix(self.attrValue_tokens,elem_idx)
        specified_id_capture_pattern = self.append_id(self.get_capture_regex(element), elem_id)
        non_id_capture_pattern = self.get_capture_regex(element)
        specified_id_gen_regex = prefix + specified_id_capture_pattern + suffix
        non_id_gen_regex = prefix + non_id_capture_pattern + suffix
   
    #####ToDo#####
    #結局 id を割り当てても、その id がついた要素を取れば良いので、idを消した時にダメになる。
    #なので、先にキャプチャするpatternのidを任意にして、いくつかの要素が抽出されたら結合する条件が必要。 

        ## non_id_gen_regex で複数要素が取れないか、正しいエレメントが取れるか、id付きの
#        if len(re.findall(non_id_gen_regex, self.attrValue)) >1 \
 #           or  not self.is_correct_generated_regex(non_id_gen_regex, self.remove_id(element_id_value))\
  #          or  not self.is_correct_generated_regex(specified_id_gen_regex, element_id_value):
        if elem_idx != 0: non_id_gen_regex = self.concat_ever_token_regex(self.token_regex[:elem_idx-1],non_id_gen_regex)

        gen_regex =  self.regex_minimize(elem_idx,element_id_value)


        #return self.remove_id(specified_id_gen_regex)
        return non_id_gen_regex

    def excute(self,):
        print(self.attrValue_id)
        for e in self.element_id_values:
            gen_regex = self.generate_element_pattern(e)
            try:
                print(gen_regex)
                print(r'{0}'.format(gen_regex), '\t',re.findall(gen_regex, self.attrValue)[0])
                extracted_element = self.extract_element(gen_regex, self.attrValue)
            except Exception as error:
                print('failed -> ', e, error)
                gen_regex = ''
                extracted_element=''

            self.extracted_element_values.append(extracted_element)
            self.element_patterns.append(gen_regex)


    def get_element_patterns(self):
        return self.element_patterns

    def get_extracted_element_values(self):
        return self.extracted_element_values

    def regex_minimize(self, gen_regex, element, cap_reg, idx):

        def capture_replace(gen_regex,element):
            new_gen_regex = gen_regex.replace('\d+(?:[\./]\d+)?', '.+?').replace(
                '(\D+?)', '(.+?)').replace('\d.*?', '.+?').replace('[A-Za-z]+\d+(?:[\./]\d+)?', '.+?')
            return new_gen_regex if self.is_correct_generated_regex(element,new_gen_regex) else gen_regex

        # キャプチャする正規表現から１つずつ前に遡り、element_valueと同じものがとれる正規表現はあるか走査する。
        new_gen_regex = gen_regex
        idx = gen_regex.find(cap_reg)
        for i in range(0, idx):
            tmp_gen_regex = gen_regex[i:]
           
            try:
                if self.is_incorrect_generated_regex(tmp_gen_regex,element):
                    new_gen_regex = tmp_gen_regex
                    break
            except:
                continue

        new_gen_regex = capture_replace(new_gen_regex, element)
        return new_gen_regex
    

def excute(S,querys,pattern):
    obj = element_RegexGenerator(S,querys,pattern)
    obj.excute()
   # extracted_element_values =  obj.extracted_element_values
    extracted_element_values = obj.get_extracted_element_values()

    print(extracted_element_values)
    return extracted_element_values

def testcase_complex3():
    S = '品番:XXX-ABCD-1-XYZ-5-123\n寸法:L1000×W300×H500mm\n重量:10kg\nカラー:ブラック\n(特記事項:強度に優れる)'
    querys = ['1000', '300', '500', '10', 'ブラック', '強度に優れる']
    pattern = '品番:[A-Z]{3}-[A-Z]{4}-\d-[A-Z]{3}-\d-\d{3}\n寸法:L\d{4}×W\d{3}×H\d{3}mm\n重量:\d{2}kg\nカラー:[\p{Hiragana}\p{Katakana}ー]+\n\(特記事項:[\p{Hiragana}\p{Katakana}ー]+\)'

    assert querys == excute(S,querys,pattern)

testcase_complex3()