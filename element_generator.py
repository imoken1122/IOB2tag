
class element_RegexGenerator:
    def __init__(self,attrValue:str, element_values: str, attrValue_pattern:str):
        self.meta_str = r'( |\n)'
        self.attrValue = attrValue
        self.element_values = element_values
        self.attrValue_pattern = attrValue_pattern

        self.attrValue_tokens = self.parse_attrValue(attrValue,element_values)
        self.element_index_token2attrValue=self.get_element_index_token2attrValue(attrValue, element_values)
        self.token_regex = self.convert_tokens_to_regex(self.attrValue_tokens)
        self.element_patterns = []
        self.extracted_element_values = []

    def get_attrValue_tokens(self):
        return self.attrValue_tokens

    def get_element_index_token2attrValue(self,attrValue,element_values):
        element_index_token2attrValue={}
        tokens = self.get_attrValue_tokens()
        start_v,start_t = 0,0

        for i, e_i in enumerate(element_values):
            end_v = attrValue.find(e_i, start_v)
            end_t = tokens.index(e_i,start_t)
            if end_v == -1:break
            element_index_token2attrValue[end_t] = end_v
            start_t = end_t + 1
            start_v = end_v +len(e_i)
        return element_index_token2attrValue
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
           # elif re.search('\d.*?', token):
           #     token_regex.append('\d.*?')
            else:
                token_regex.append('.+?')

        return token_regex

    def get_capture_regex(self, token):
        if re.search('\n', token):
            return '(' + re.sub('[^\n]+','.+?',token) + ')'
        elif re.search('^\d+(?:，?[\./]\d+)?$', token):
            return '([\d，]+(?:[\./]\d+)?)'
        elif regex.search('^\d+(?:[\./]\d+)?[\p{Script=Han}\p{Script=Katakana}\p{Script=Hiragana}A-Za-zー]+$', token):
            return '([\d，]+(?:[\./]\d+)?\D+?)'
        elif re.search('^[A-Z]+\d+(?:[\./]\d+)?$', token):
            return '([A-Za-z]+\d+(?:[\./]\d+)?)'
        elif re.search('^[A-Za-z]+',token):
            return '([A-Za-z]+?)'
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
            if not self.is_contained_attrValue_pattern(prefix):
                if re.search('^[\d，]+([\./]d+)?$', prefix):
                    prefix = '[\d\./]+'

                elif re.search('^\D+$', prefix) :
                    prefix = '\D+?'
                elif re.search('^[\d\D]+$', prefix):
                    prefix = '[\d\D]+?'
        else:
            prefix = '^'

        if idx != len(tokens)-1:
            suffix = self.escape_token(tokens[idx+1])
            suffix = self.extract_element('(^[A-Za-z]+)',suffix) if re.search('(^[A-Za-z]+)',suffix) and  suffix in self.element_values else suffix
            if not self.is_contained_attrValue_pattern(suffix):
                if re.search('\\d', suffix[0]):
                    suffix = '\d'

                elif re.search('[A-Za-z]', suffix):
                    suffix = '[A-Za-z]'
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
                print("E : Syntax of the generated element_pattern is incorrect -> \nattrValue : {0}\nelement_value : {1}\nelement_pattern : {2}".format(self.attrValue ,element, gen_regex))
            extracted_element = ''
        return extracted_element
    def extract_element_and_span(self,gen_regex,verbose=False):
        try:
            first_elem_info = next(re.finditer(gen_regex,self.attrValue ))
            return (first_elem_info.groups(1)[0], first_elem_info.start(1))
        except:
            return (None, None)


    def is_correct_generated_regex(self,gen_regex,element,elem_idx_on_token):
        extracted_element,extracted_elem_idx = self.extract_element_and_span(gen_regex)
        elem_idx_on_attrValue = self.element_index_token2attrValue[elem_idx_on_token]
            
        return extracted_element == element and extracted_elem_idx == elem_idx_on_attrValue
    
    def concat_ever_token_regex(self,elem_idx,gen_regex):
        if elem_idx==0: return gen_regex
        ever_regex = self.token_regex[:elem_idx-1]
        return '^' + "".join(ever_regex[:]) + gen_regex


    def generate_element_pattern(self,attrValue_tokens, element_value:str,elem_idx):

        prefix, suffix = self.get_prefix_and_suffix(attrValue_tokens,elem_idx)

        capture_regex =  self.get_capture_regex(element_value)
        gen_regex = prefix + capture_regex + suffix
        minimized_gen_regex =  self.regex_minimize(gen_regex,element_value, elem_idx)

        return minimized_gen_regex

    def excute(self,):
        pre_idx = 0
        attrValue_tokens = self.get_attrValue_tokens()

        for elem in self.element_values:
            elem_idx = attrValue_tokens.index(elem,pre_idx)
            gen_regex = self.generate_element_pattern(attrValue_tokens,elem, elem_idx)
            try:
                #print(r'{0}'.format(gen_regex))
                #print(re.findall(gen_regex, self.attrValue)[0])

                extracted_element = self.extract_element(gen_regex, self.attrValue,True)
            except Exception as error:
                gen_regex = ''
                extracted_element=''

            self.extracted_element_values.append(extracted_element)
            self.element_patterns.append(gen_regex)

            pre_idx = elem_idx+1


    def get_element_patterns(self):
        return self.element_patterns

    def get_extracted_element_values(self):
        return self.extracted_element_values

    def regex_minimize(self, gen_regex, element, elem_idx_on_token,):

        def capture_replace(gen_regex):
            new_gen_regex = gen_regex
            replace_regex_list=[
                ('[\d，]+(?:[\./]\d+)?', '\d.*?'),
                ('[\d，]+(?:[\./]\d+)?\D+?', '\d.*?'),
                ('[A-Za-z]+\d+(?:[\./]\d+)?', '.+?'),
                ('(\D+?)', '(.+?)'),
                ("\d.*?",".+?")
            ]
            for rep in replace_regex_list:
                tmp_gen_regex = gen_regex.replace(rep[0],rep[1])
                if self.is_correct_generated_regex(tmp_gen_regex, element, elem_idx_on_token):
                    new_gen_regex = tmp_gen_regex if len(tmp_gen_regex) < len(new_gen_regex) else new_gen_regex
            return new_gen_regex

        def regex_lookahead_for_matching_element_value(gen_regex):
        # キャプチャする正規表現から１つずつ前に遡り、element_valueと同じものがとれる正規表現はあるか走査する。

            elem_idx_on_attrValue = self.element_index_token2attrValue[elem_idx_on_token]
            new_gen_regex =  self.concat_ever_token_regex(elem_idx_on_token, gen_regex)
            gen_regex_idx = new_gen_regex.find(gen_regex)
            for i in reversed(range(0, gen_regex_idx+1)):
                tmp_gen_regex = new_gen_regex[i:]
            
                try:
                    if self.is_correct_generated_regex(tmp_gen_regex, element, elem_idx_on_token):
                        new_gen_regex = tmp_gen_regex
                        break
                except:
                    continue
            return new_gen_regex


        new_gen_regex = regex_lookahead_for_matching_element_value(gen_regex)
        new_gen_regex = capture_replace(new_gen_regex)
        new_gen_regex = re.sub('(\.\+\?){2,}','.+?',new_gen_regex)
        return new_gen_regex
    
