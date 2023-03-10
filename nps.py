#@title create complemented nemerical_attrValue_splitting data

from tqdm import tqdm_notebook as tqdm
class ComplementingNemericalAttrValueSplittingData:
    def __init__(self,master_df, bert_model, attrValue_RegexGenerator, element_RegexGenerator):
        #self.req_attrValues = req_attrValues
        self.master_df = master_df
        self.bert = bert_model
        self.master_df_attrValues = master_df['attrName'].unique().to_numpy()
        self.NAS_data = []
        self.attrValue_RegexGenerator = attrValue_RegexGenerator
        self.element_RegexGenerator = element_RegexGenerator


    def _grouping_same_rows(self,df,conditional_col): # -> dataframe, dict
        # pandas 
        #df[id] = df.groupby(['attrCode','attrValue','attrValue_example']).ngroup()
        #grouped_id = df.groupby(['id']).apply(lambda x:x.to_dict(orient='records'))
        #return grouped_id.to_dict()

        tmp_df = df.with_row_count("idx").groupby(conditional_col,   #['attrCode','attrValue','attrValue_example'],
                    maintain_order=True,).agg(pl.col("idx")).with_row_count("ngroup_id").explode("idx").drop('idx')
        df = df.with_columns( tmp_df.get_column("ngroup_id").alias("ngroup_id"))
        cols = df.columns
        grouped_original = dict()
        for ng in df.select('ngroup_id').unique().to_numpy().reshape(-1):
            group_rows = df.filter(pl.col('ngroup_id')==ng).to_numpy()
            data = list(map(lambda x :{c : xi for c, xi in zip(cols,x)},group_rows))
            if id not in grouped_original:
                grouped_original[ng] = data
            else:
                grouped_original[ng].append(data)
        return df, grouped_original 


    def _complement_attrValue_pattern(self):
        pass

    def extract_element(self,attrValue:str ,pattern : str):# -> str
        p = pattern
        if p == "": 
            return ""
        if p.find("\p")!=-1:
            p = p.replace("{","{Script=")
        try:
            elm = regex.findall(p,attrValue)[0]
        except Exception as e:
            print("E : Referenced element_pattern is incorrect ->\n" ,"attrValue : ", attrValue,"\nelement_pattern : ",p)
            elm=""
        return elm

    def _generate_element_patterns(self,attrValue:str, element_values: list, pattern : str):

        rg = self.element_RegexGenerator(attrValue, element_values, pattern)
        element_patterns = []
        try:
            rg.excute()
            element_patterns = rg.get_element_patterns()
        except:
            print('E : Failed to generate element_patterns ->\n',"attrValue : ", attrValue,"\nelement_values : ", element_values)
            element_patterns = rg.element_patterns + [''] * (len(element_values) - len(rg.element_patterns))

        return element_patterns

    def _generate_attrValue_pattern(self,attrValue):
        return self.attrValue_RegexGenerator._attrValue2regex(attrValue)


    def _get_element_label(self):
        pass
    
    def _get_filter_data(self,df,condition, is_head=False):
        if is_head:
            df_row = df.filter(condition).head(1)
        else :
            df_row = df.filter(condition)

        return df_row


    def _select_rows_by_category(self,df_rows): # -> dict
        _,n_group_df_rows = self._grouping_same_rows(df_rows,['target_categoryCode'])
        ### 
        # 最適な key を選択する処理 (attrNameが近い、element_label が近いもの選択する)
        ###
        key = list(n_group_df_rows.keys())[0]
        data = n_group_df_rows[key]
        #return pl.Dataframe(data,columns = self.target_df.columns)
        return data

    def _refer_row_elements_mastersheet(self,target_df_row):
        selected_master_df_rows = None

        #過去のデータを取得する条件を取得
        filter_conditions = self._get_filter_conditions(target_df_row)

        for cond in filter_conditions:
            #条件に合う過去のデータを参照
            master_df_rows = self._get_filter_data(self.master_df,cond)
            if len(master_df_rows) == 0: continue

            #過去のデータの中で尤も近いデータを参照
            selected_master_df_rows = self._select_rows_by_category(master_df_rows)


            #elementが抽出できなかったら過去データは参照しないで BERT にまかせる
            target_attrValue = target_df_row.get_column("attrValue_example")[0]
            for dic in selected_master_df_rows:
                element= self.extract_element(target_attrValue, dic["element_pattern"])
                if element != "":
                    dic['extracted_element_value'] = element
                else:
                    return None

            #どれか1つでもマッチしたらbreak
            break

        return selected_master_df_rows

    def _predicte_row_elements_using_bert(self, target_df_row): #->dict
        av = target_df_row.get_column('attrValue_example')[0]
        av_pattern = target_df_row.get_column('attrValue_pattern')[0]
        entities = self.bert._predicte_element_label(av)
        element_values = [ e['name'] for e in entities]

        element_patterns = self._generate_element_patterns(av,element_values,av_pattern)
        entity_lists = [
                        {
                         'element_label': self.bert.id2type[e['type_id']] ,
                         'element_pattern': element_patterns[i], 
                         'extracted_element_value':e['name']  #if element_patterns[i] != "" else ""
                         }
                         for i, e in enumerate(entities)]

        #return pl.Dataframe(entity_lists,columns = ['element_label','element_pattern','extracted_element_value'])
        return entity_lists

    def _create_new_element(self,target_df_row):

        new_rows_elements = None
        #過去のデータからelementを参照
        new_rows_elements = self._refer_row_elements_mastersheet(target_df_row)
        if new_rows_elements == None:
            #過去のデータになければ、BERTでelementを予測
            new_rows_elements = self._predicte_row_elements_using_bert(target_df_row)
        return new_rows_elements


    def _create_new_rows(self,target_df_row, new_rows_elements):
        
        if len(new_rows_elements) == 0: 
            return target_df_row.select(pl.all()).to_numpy()

        #elementの数だけ行を複製
        new_rows = pl.concat([target_df_row]*len(new_rows_elements)).to_dict()

        series_elements_labels = pl.Series( [ e['element_label'] for e in new_rows_elements])
        series_element_patterns= pl.Series( [ e['element_pattern'] for e in new_rows_elements])
        series_extracted_value = pl.Series( [ e['extracted_element_value'] for e in new_rows_elements])
        new_rows['element_label'] = series_elements_labels
        new_rows['element_pattern'] = series_element_patterns
        new_rows['extracted_element_value'] = series_extracted_value

        new_rows = pl.DataFrame(new_rows)
        new_rows = new_rows.unique(subset=["element_pattern"])

        return new_rows.select(pl.all()).to_numpy()



    def _get_filter_conditions(self, row):
        def get_similar_attrName(attrName:str):
            similar_name2score = extract(attrName, self.master_df_attrValues)
            return similar_name2score[0][0]

        code,name,pattern = row.get_column('attrCode')[0],row.get_column('attrName')[0],row.get_column('attrValue_pattern')[0]
        sim_name = get_similar_attrName(name)
        spae = row.get_column('splitting_rules_attrValue_example')[0]

        conditions = [
            (pl.col('attrCode') == code) & (pl.col('attrName') == name) & (pl.col('attrValue_pattern') == pattern),
            
            (pl.col('attrName') == sim_name) & (pl.col('attrValue_pattern') == pattern),

            (pl.col('attrValue_example') == spae)  & (pl.col('attrValue_pattern') == pattern),

            
        ]
        return conditions

    def _is_sequential_attrValue(self,target_df_row):
        attrValue = target_df_row.get_column("attrValue_example")[0]
        is_seq,split_str,split_attrValue = self.attrValue_RegexGenerator.is_sequential(attrValue)
        return is_seq

    def _complementing_NASData(self,target_df):
        print("\n\033[32mStarting data complementation process\033[0m\n")
        target_df, n_group_target_df = self._grouping_same_rows(target_df,['attrCode','attrName','attrValue_example'])
        for row_id,_ in tqdm(n_group_target_df.items()):

            target_df_row = self._get_filter_data(target_df,pl.col('ngroup_id')==row_id,is_head=True)

          #  if target_df_row.get_column('rnk')[0] == '': 
           #     self.NAS_data.append(target_df_row)
            #    continue
            
            if target_df_row.get_column("splitting_rules_attrValue_example")[0] == "":
                df_dic = target_df_row.to_dict()
                df_dic["attrValue_pattern"] = self._generate_attrValue_pattern(df_dic["attrValue_example"][0])
                target_df_row = pl.DataFrame(df_dic)

           # if self._is_sequential_attrValue(target_df_row):
            # new_rows_elements = self._create_new_element(tmp_target_df_row)
            new_rows_elements = self._create_new_element(target_df_row)
            new_rows = self._create_new_rows(target_df_row,new_rows_elements)
            self.NAS_data.extend(new_rows)
        print("\n\033[32mSpreadSheet data created succesfully\033[0m\n")
        return self._to_dataframe(self.NAS_data,target_df_row.columns)

    def _to_dataframe(self,data,col):
        output = pd.DataFrame(data,columns =col)
        #output["rnk"] = output.rnk.replace("","-1").replace("None","-1")
        #output["rnk"] = output["rnk"].astype(int)
        #output.sort_values(by=["ngroup_id"],inplace=True)
        return output

    def _write_target_spreadsheet(self,df,url,name):
        ss = gc.open_by_url(url)
        new_worksheet = ss.add_worksheet(title=name,rows = 30, cols = 20)
        try:
            #set_with_dataframe(st,df,include_index=False,include_column_header = False )
            set_with_dataframe(new_worksheet, output_df)
            print("\033[32mData written to SpreadSheet sucessfully\033[0m")
        except:
            print("Stoped to write data to SpreadSheet")

    def _is_same_two_unique_df(self,output_df,target_df):
        out = output_df.drop_duplicates(subset=["attrCode","attrName","attrValue_example"])[["attrCode","attrValue_example"]]
        target = target_df.unique(subset=["attrCode","attrName","attrValue_example"]).select(pl.col(["attrCode","attrValue_example"]))
        target = target.to_numpy()
        out = out.values
        if np.sum(target == out ) == (len(out) + len(target)):
            print("The two data are equal")
        else:
            print("not equal")
    


