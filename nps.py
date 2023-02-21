import pandas as pd
import polars as pl
import itertools
import random
import json
from tqdm import tqdm
import numpy as np
import unicodedata
from rapidfuzz.process import extract, cdist
import torch
from torch.utils.data import DataLoader
from transformers import BertJapaneseTokenizer, BertForTokenClassification
import pytorch_lightning as pl
import re,regex

TARGET_SHEET_URL = ''
MASTER_SHEET_URL = ''
SAGYO_SHEET_URL = ''
MODEL_NAME = 'cl-tohoku/bert-base-japanese-whole-word-masking'

class NER_tokenizer_BIO(BertJapaneseTokenizer):

    # 初期化時に固有表現のカテゴリーの数`num_entity_type`を
    # 受け入れるようにする。
    def __init__(self, *args, **kwargs):
        self.num_entity_type = kwargs.pop('num_entity_type')
        super().__init__(*args, **kwargs)

    def encode_plus_tagged(self, text, entities, max_length):
        """
        文章とそれに含まれる固有表現が与えられた時に、
        符号化とラベル列の作成を行う。
        """
        # 固有表現の前後でtextを分割し、それぞれのラベルをつけておく。
        splitted = [] # 分割後の文字列を追加していく
        position = 0
        for entity in entities:
            start = entity['span'][0]
            end = entity['span'][1]
            label = entity['type_id']
            splitted.append({'text':text[position:start], 'label':0})
            splitted.append({'text':text[start:end], 'label':label})
            position = end
        splitted.append({'text': text[position:], 'label':0})
        splitted = [ s for s in splitted if s['text'] ]

        # 分割されたそれぞれの文章をトークン化し、ラベルをつける。
        tokens = [] # トークンを追加していく
        labels = [] # ラベルを追加していく
        for s in splitted:
            tokens_splitted = self.tokenize(s['text'])
            label = s['label']
            if label > 0: # 固有表現
                # まずトークン全てにI-タグを付与
                labels_splitted =  \
                    [ label + self.num_entity_type ] * len(tokens_splitted)
                # 先頭のトークンをB-タグにする
                labels_splitted[0] = label
            else: # それ以外
                labels_splitted =  [0] * len(tokens_splitted)
            
            tokens.extend(tokens_splitted)
            labels.extend(labels_splitted)

        # 符号化を行いBERTに入力できる形式にする。
        input_ids = self.convert_tokens_to_ids(tokens)
        encoding = self.prepare_for_model(
            input_ids, 
            max_length=max_length, 
            padding='max_length',
            truncation=True
        ) 

        # ラベルに特殊トークンを追加
        labels = [0] + labels[:max_length-2] + [0]
        labels = labels + [0]*( max_length - len(labels) )
        encoding['labels'] = labels

        return encoding

    def encode_plus_untagged(
        self, text, max_length=None, return_tensors=None
    ):
        """
        文章をトークン化し、それぞれのトークンの文章中の位置も特定しておく。
        IO法のトークナイザのencode_plus_untaggedと同じ
        """
        # 文章のトークン化を行い、
        # それぞれのトークンと文章中の文字列を対応づける。
        tokens = [] # トークンを追加していく。
        tokens_original = [] # トークンに対応する文章中の文字列を追加していく。
        words = self.word_tokenizer.tokenize(text) # MeCabで単語に分割
        for word in words:
            # 単語をサブワードに分割
            tokens_word = self.subword_tokenizer.tokenize(word) 
            tokens.extend(tokens_word)
            if tokens_word[0] == '[UNK]': # 未知語への対応
                tokens_original.append(word)
            else:
                tokens_original.extend([
                    token.replace('##','') for token in tokens_word
                ])

        # 各トークンの文章中での位置を調べる。（空白の位置を考慮する）
        position = 0
        spans = [] # トークンの位置を追加していく。
        for token in tokens_original:
            l = len(token)
            while 1:
                if token != text[position:position+l]:
                    position += 1
                else:
                    spans.append([position, position+l])
                    position += l
                    break

        # 符号化を行いBERTに入力できる形式にする。
        input_ids = self.convert_tokens_to_ids(tokens) 
        encoding = self.prepare_for_model(
            input_ids, 
            max_length=max_length, 
            padding='max_length' if max_length else False, 
            truncation=True if max_length else False
        )
        sequence_length = len(encoding['input_ids'])
        # 特殊トークン[CLS]に対するダミーのspanを追加。
        spans = [[-1, -1]] + spans[:sequence_length-2] 
        # 特殊トークン[SEP]、[PAD]に対するダミーのspanを追加。
        spans = spans + [[-1, -1]] * ( sequence_length - len(spans) ) 

        # 必要に応じてtorch.Tensorにする。
        if return_tensors == 'pt':
            encoding = { k: torch.tensor([v]) for k, v in encoding.items() }

        return encoding, spans

    @staticmethod
    def Viterbi(scores_bert, num_entity_type, penalty=10000):
        """
        Viterbiアルゴリズムで最適解を求める。
        """
        m = 2*num_entity_type + 1
        penalty_matrix = np.zeros([m, m])
        for i in range(m):
            for j in range(1+num_entity_type, m):
                if not ( (i == j) or (i+num_entity_type == j) ): 
                    penalty_matrix[i,j] = penalty
        
        path = [ [i] for i in range(m) ]
        scores_path = scores_bert[0] - penalty_matrix[0,:]
        scores_bert = scores_bert[1:]

        for scores in scores_bert:
            assert len(scores) == 2*num_entity_type + 1
            score_matrix = np.array(scores_path).reshape(-1,1) \
                + np.array(scores).reshape(1,-1) \
                - penalty_matrix
            scores_path = score_matrix.max(axis=0)
            argmax = score_matrix.argmax(axis=0)
            path_new = []
            for i, idx in enumerate(argmax):
                path_new.append( path[idx] + [i] )
            path = path_new

        labels_optimal = path[np.argmax(scores_path)]
        return labels_optimal

    def convert_bert_output_to_entities(self, text, scores, spans):
        """
        文章、分類スコア、各トークンの位置から固有表現を得る。
        分類スコアはサイズが（系列長、ラベル数）の2次元配列
        """
        assert len(spans) == len(scores)
        num_entity_type = self.num_entity_type
        
        # 特殊トークンに対応する部分を取り除く
        scores = [score for score, span in zip(scores, spans) if span[0]!=-1]
        spans = [span for span in spans if span[0]!=-1]

        # Viterbiアルゴリズムでラベルの予測値を決める。
        labels = self.Viterbi(scores, num_entity_type)

        # 同じラベルが連続するトークンをまとめて、固有表現を抽出する。
        entities = []
        for label, group \
            in itertools.groupby(enumerate(labels), key=lambda x: x[1]):
            
            group = list(group)
            start = spans[group[0][0]][0]
            end = spans[group[-1][0]][1]

            if label != 0: # 固有表現であれば
                if 1 <= label <= num_entity_type:
                     # ラベルが`B-`ならば、新しいentityを追加
                    entity = {
                        "name": text[start:end],
                        "span": [start, end],
                        "type_id": label
                    }
                    entities.append(entity)
                else:
                    # ラベルが`I-`ならば、直近のentityを更新
                    entity['span'][1] = end 
                    entity['name'] = text[entity['span'][0]:entity['span'][1]]
                
        return entities
class BertForTokenClassification_pl(pl.LightningModule):
        
    def __init__(self, model_name, num_labels, lr):
        super().__init__()
        self.save_hyperparameters()
        self.bert_tc = BertForTokenClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        )
        
    def training_step(self, batch, batch_idx):
        output = self.bert_tc(**batch)
        loss = output.loss
        self.log('train_loss', loss)
        return loss
        
    def validation_step(self, batch, batch_idx):
        output = self.bert_tc(**batch)
        val_loss = output.loss
        self.log('val_loss', val_loss)
        
    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=self.hparams.lr)

class NER_Bert:
    def __init__(self, model_path,model_name, entity_types):
        model = BertForTokenClassification_pl.load_frome_checkpoint(model_path)
        self.bert_tc = model.bert_tc
        self.tokenizer = NER_tokenizer_BIO.from_pretrained(model_name, num_entity_type = len(entity_types))
        self.normalize = lambda s: unicodedata.normalize("NFKC",s)
        self.id2type = {i+1:t for i,t in enumerate(entity_types)}

    def _predicte_element_label(self, attrValue):
        text = self.normalize(attrValue)
        encoding, spans = self.tokenizer.encode_plus_untagged(
            text, return_tensors='pt'
        )
        encoding = { k: v.cuda() for k, v in encoding.items() } 
        
        with torch.no_grad():
            output = self.bert_tc(**encoding)
            scores = output.logits
            scores = scores[0].cpu().numpy().tolist()
            
        # 分類スコアを固有表現に変換する
        entities_predicted = self.tokenizer.convert_bert_output_to_entities(
            text, scores, spans
        )
        return entities_predicted

    def _create_new_rows(self):
        pass

class NemericalAttrValueSplittingSheet:
    def __init__(self,target_df,master_df,req_attrValues, bert_model):
        self.req_attrValues = req_attrValues
        self.master_df = master_df
        self.target_df = target_df
        self.bert = bert_model
        self.master_df_attrValues = master_df['attrName'].unique().to_numpy()


    def _grouping_same_rows(self,df,conditional_col) -> dict:
        # pandas 
        #df[id] = df.groupby(['attrCode','attrValue','attrValue_example']).ngroup()
        #grouped_id = df.groupby(['id']).apply(lambda x:x.to_dict(orient='records'))
        #return grouped_id.to_dict()

        df.with_row_count("idx").groupby(conditional_col,   #['attrCode','attrValue','attrValue_example'],
                    maintain_order=True,).agg(pl.col("idx")).with_row_count("ngroup").explode("idx").drop('idx')
        cols = df.columns
        grouped_original = dict()
        
        for ng in df.select('id').unique().to_numpy():
            group_rows = filter(pl.col('ngroup')==ng).to_numpy()
            data = list(map(lambda x :{c : xi for c, xi in zip(cols,x)},group_rows))
            if id not in grouped_original:
                grouped_original[ng] = data
            else:
                grouped_original[ng].append(data)
        return grouped_original 


    def _complement_attrValue_pattern(self):
        pass

    def _extracted_elements(self,attrValue:str,patterns:list):
        pass

    def _generate_element_patterns(self,attrValue:str, querys: list, pattern : str):

        rg = RegexGenerator(attrValue, querys, pattern)
        element_patterns = []
        try:
            rg.excute()
            element_patterns = rg.query_regex
        except:
            print('failed generate element patterns', attrValue,querys)
            element_patterns = rg.query_regex + [''] * (len(querys) - len(rg.query_regex))

        return element_patterns

    def _get_element_label(self):
        pass
    
    def _get_filter_data(self,df,condition, is_head=False):
        if is_head:
            df_row = df.filter(condition).head(1)
        else :
            df_row = df.filter(condition)

        return df_row


    def _select_rows_by_category(self,df_rows): # -> dict
        n_group_df_rows = self._grouping_same_rows(df_rows,['target_categoryCode'])
        ### 
        # 最適な key を選択する処理 (attrNameが近い、element_label が近いもの選択する)
        ###
        key = list(n_group_df_rows.keys())[0]
        data = n_group_df_rows[key]
        #return pl.Dataframe(data,columns = self.target_df.columns)
        return data

    def _refer_row_elements_mastersheet(self,target_df_row):

        filter_conditions = self._get_filter_conditions(target_df_row)
        for cond in filter_conditions:
            #条件に合う過去のデータを参照
            master_df_rows = self._get_filter_data(self.master_df,cond)
            if len(master_df_rows) == 0: continue
            #尤も近いデータを参照
            selected_master_df_rows = self._select_rows_by_category(master_df_rows)


            for dic in selected_master_df_rows:
                element= self.extract_element(dic['element_pattern'])
                if element != None:
                    dic['extracted_element_value'] = element
                else: 
                    #elementが抽出できなかったら過去データは参照しない
                    return None

            #どれか1つでもマッチしたらbreak
            break

        return selected_master_df_rows

    def _predicte_using_bert(self, target_df_row): #->dict
        av = target_df_row.get_column['attrValue'][0]
        av_pattern = target_df_row.get_column['attrValue_pattern'][0]
        entities = self.bert.predicte_element_label(av)
        querys = [ e['name'] for e in entities]

        element_patterns = self._generate_element_patterns(av,querys,av_pattern)
        entity_lists = [
                        {
                         'element_label': self.bert.id2type[e['type_id']] ,
                         'element_pattern': element_patterns[i], 
                         'extracted_element_value':e['name'] 
                         }
                         for i, e in enumerate(entities)]
        #return pl.Dataframe(entity_lists,columns = ['element_label','element_pattern','extracted_element_value'])
        return entity_lists


    def _create_new_rows(self,target_df_row):

        new_rows_elements = self._refer_row_elements_mastersheet(target_df_row)
        if new_rows_elements == None:
            new_rows_elements = self._predicte_row_elements_using_bert(target_df_row)

        if len(new_rows_elements) == 0: return target_df_row

        #elementの数だけ行を複製
        new_rwos = pl.concat([target_df_row]*len(new_rows_elements)).to_dict()

        series_elements_labels = pl.Series( [ e['element_label'] for e in new_rows_elements])
        series_element_patterns= pl.Series( [ e['element_pattern'] for e in new_rows_elements])
        series_extracted_value = pl.Series( [ e['extracted_element_value'] for e in new_rows_elements])
        new_rwos['element_label'] = series_elements_labels
        new_rwos['element_pattern'] = series_element_patterns
        new_rwos['element_extracted_value'] = series_extracted_value

        new_rwos = pl.DataFrame(new_rwos)
        return new_rwos



    def _get_filter_conditions(self, row):
        def get_similar_attrName(attrName:str):
            similar_name2score = extract(attrName, self.master_df_attrValues)
            return similar_name2score[0][0]

        code,name,pattern = row.get_column['attrCode'][0],row.get_column['attrValue'][0],row.get_column['attrValue_pattern'][0]
        sim_name = get_similar_attrName(name)
        spae = row.get_column['splitting_rules_attrValue_example'][0]

        conditions = [
            (pl.col('attrCode') == code) & (pl.col('attrName') == name) & (pl.col('attrValue_pattern') == pattern),
            
            (pl.col('attrName') == sim_name) & (pl.col('attrValue_pattern') == pattern),

            (pl.col('attrValue_example') == spae)  & (pl.col('attrValue_pattern') == pattern),

            
        ]
        return conditions

    def _create_NASsheet(self,target_df):

        n_group_target_df = self._grouping_same_rows(target_df,['attrCode','attrValue','attrValue_example'])
        for row_id,_ in n_group_target_df.items():

            target_df_row = self._get_filter_data(target_df,pl.col('id')==row_id,is_head=True)
            if target_df_row.get_column('rnk')[0] == '': 
                self.NASsheet.append(target_df_row)
                continue
            
            new_rows = self._create_new_rows(target_df_row)
            self.NASsheet.extend(new_rows)

            



def load_spreadsheet(url : str):
    pass

        


def main():
    master_df = load_spreadsheet(MASTER_SHEET_URL)
    target_df = load_spreadsheet(TARGET_SHEET_URL)
    sagyo_df = load_spreadsheet(SAGYO_SHEET_URL)
    req_attrValues = sagyo_df['attrValue']
    navss = NemericalAttrValueSplittingSheet(target_df,master_df, req_attrValues)

