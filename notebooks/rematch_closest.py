import os

import editdistance
import numpy as np
import pandas as pd
import psycopg2

# read environment variables from vars.env
from dotenv import load_dotenv
from tqdm import tqdm


load_dotenv("../vars.env")

# connect to postgresql db on localhost, post 5432, using user and password from vars.env

import os

import psycopg2


# Define the database credentials
db_host = os.getenv("POSTGRES_HOST")
db_name = os.getenv("POSTGRES_DB")
db_user = os.getenv("POSTGRES_USER")
db_password = os.getenv("POSTGRES_PWD")


def edit_distance(s1, s2):
    return editdistance.eval(s1, s2)


dataset = "Spanish"

sql_script = f"""
SELECT dataset.name, sample.id, sample.filename, sample.local_trimmed_path, sample.original_text, sample.asr_text, sample.wer, sample.trimmed_audio_duration as duration
FROM sample
JOIN dataset ON sample.dataset_id = dataset.id
WHERE dataset.name LIKE '%' || '{dataset}' || '%';
"""

# Connect to the database
conn = psycopg2.connect(host=db_host, database=db_name, user=db_user, password=db_password)

# Execute the SQL script into pandas dataframe with column names
df = pd.read_sql_query(sql_script, conn)
# group by name and then create a dict of the grouped dataframes

df_dict = {k: v for k, v in df.groupby("name")}
df_matched_list = []
for df_name, df_sentences in df_dict.items():
    print(f"Processing {df_name}")
    df_sentences = df_sentences.reset_index(drop=True)

    sentences = {}
    inverseSentences = {}

    segments = {}

    print(f"There are {len(df_sentences)} sentences in this range")
    for index, row in df_sentences.iterrows():
        sentenceNum = int(index)
        sentence = row["original_text"]
        sentences[sentenceNum] = sentence

        segments[sentenceNum] = row
        if sentence not in inverseSentences:
            inverseSentences[sentence] = sentenceNum
        else:
            tmp = sentence
            while tmp in inverseSentences:
                tmp += " _"
            inverseSentences[tmp] = sentenceNum

    sentenceNumber = -1

    segments_list = [v for k, v in segments.items()]
    sentences_list = [v for k, v in sentences.items()]
    distances_matrix = np.ones((len(segments_list), len(sentences))) * 1000

    for ik in tqdm(range(len(segments_list))):
        # for jk in range(ik-500, min(len(segments_list), ik+500)):
        for jk in range(len(sentences_list)):
            try:
                distances_matrix[ik, jk] = edit_distance(segments_list[ik]["asr_text"], sentences_list[jk]) / min(
                    len(segments_list[ik]["asr_text"]), len(sentences_list[jk])
                )
            except:
                distances_matrix[ik, jk] = np.inf

    # get the best match for each segment
    best_matches = np.argmin(distances_matrix, axis=1)
    best_matched_sentences = [sentences_list[k] for k in best_matches]

    # # make a dataframe
    rows = []
    best_matched_sentences = [sentences_list[k] for k in best_matches]

    # print the results
    for ik in tqdm(range(len(segments_list))):
        asr = segments_list[ik]["asr_text"]
        sentence = best_matched_sentences[ik]
        ed_dist = distances_matrix[ik, best_matches[ik]]
        try:
            len_dif = abs(len(asr) - len(sentence)) / min(len(asr), len(sentence))
        except:
            len_dif = np.inf
        sentenceNumber = inverseSentences[sentence]
        if ed_dist < 0.25 and len_dif < 0.15:
            status = "assigned"
        else:
            status = "not_assigned"

        row = {
            "status": status,
            "originalNumber": ik,
            "original_id": segments_list[ik]["id"],
            "assigned_id": segments[sentenceNumber]["id"],
            "original_sentence": sentences_list[ik],
            "assigned_sentence": sentence,
            "ed_dist": ed_dist,
            "len_dif": len_dif,
        }

        row.update(segments_list[ik])
        rows.append(row)
    # if there is inf  drop it
    df_matched_ = pd.DataFrame(rows)
    df_matched_ = df_matched_[df_matched_["ed_dist"] != np.inf]

    diff = df_matched_[df_matched_.original_id != df_matched_.assigned_id]
    diff = diff[diff.status == "assigned"]
    diff = diff.sort_values("ed_dist").drop_duplicates("assigned_id", keep="first")

    if len(diff) > 0:
        diff.to_csv(f"diff_{df_name}.csv", index=False)
        print(f"Found {len(diff)} differences")
    df_matched_list.append(diff)


df_matched = pd.concat(df_matched_list)
df_matched = df_matched.sort_values("ed_dist").drop_duplicates("assigned_id", keep="first")


df_matched.to_csv("matched.csv", index=False)

print(f"Matched {len(df_matched)} sentences")
