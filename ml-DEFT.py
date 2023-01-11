# -*- coding: utf-8 -*-
"""

Task to be performed : 
**Task 3 of the 2009 Text Mining Challenge (TMC): **
- learning to classify by political party interventions in the European Parliament. (The data are available on the [DEFT](https://deft.lisn.upsaclay.fr/) website, their description and the task description on [the 2009 edition page](https://deft.lisn.upsaclay.fr/2009/))

To do: 
1) propose a classifier(s) for this task, study its (their) performance on this task. 
2) Compare to the information given in the [proceedings](https://deft.lisn.upsaclay.fr/actes/2009/pdf/0_grouin.pdf).

"""

!pip install spacy_sentence_bert

from google.colab import drive
drive.mount('/content/drive')

from bs4 import BeautifulSoup
import numpy as np
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.svm import SVC 
from sklearn.feature_extraction.text import TfidfVectorizer
import spacy_sentence_bert
from tqdm import tqdm
#import tensorflow as tf

# Set seed
np.random.seed(500) #setting the seed ensures that the generator produces the same sequence of random numbers every time the code is run.
tqdm.pandas() # initialize tqdm for pandas, function that registers the tqdm progress bar with pandas, so that it is displayed when using certain pandas functions

# Package specific installs
nltk.download('stopwords')
nltk.download('punkt')

# CONSTANTS
LANG = "english" # change for model to work on other languages fr/it (may still need to update nltk and spacy_sentence_bert)

# We read the dataset from relevant XML files and parse the training data and test data 
xml_string_test = "/content/drive/MyDrive/Projet ML/Corpus d'apprentissage/deft09_parlement_appr_en.xml"
xml_string_train = "/content/drive/MyDrive/Projet ML/Corpus de test/deft09_parlement_test_en.xml"
# We'll use this one later to add to the train keys
train_ids = "/content/drive/MyDrive/Projet ML/Données de référence/deft09_parlement_ref_en.txt"
with open(xml_string_test, 'r') as f:
	file = f.read() 
# 'xml' is the parser used. For html files, which BeautifulSoup is typically used for, it would be 'html.parser'.
xml_test_soup = BeautifulSoup(file, 'xml')

""" 
We'll repeat this process for our training data 
"""

with open(xml_string_train, 'r') as f:
	file = f.read() 
# 'xml' is the parser used. For html files, which BeautifulSoup is typically used for, it would be 'html.parser'.
xml_train_soup = BeautifulSoup(file, 'xml')
# we'll check that the xml is read correctly
print(xml_test_soup.doc)
print("*"*100)
print(xml_train_soup.doc)
print(xml_string_train[0])

# We now find all relevant parties (PARTI) and use regex to omit the integer increment found in the train data
xml_test_values = xml_test_soup.findAll("PARTI")
xml_test_keys = xml_test_soup.findAll("texte")

xml_train_values = xml_train_soup.findAll("PARTI")
xml_train_keys = xml_train_soup.findAll("texte")

pun = '''‘’!()-[]{};:'"\,<>./?@#$%^&*_~'''  # regex catchall for unnecessary punctuation

# remove lower case
xml_test_keys_lowered = [i.text.lower() for i in xml_test_keys]
#print(xml_test_keys_lowered[0])
xml_train_keys_lowered = [i.text.lower() for i in xml_train_keys]
#print(xml_train_keys_lowered[0])

# remove punctuation
xml_test_keys_cleaned = [i.translate(str.maketrans('','', pun)) for i in xml_test_keys_lowered]
print(xml_test_keys_cleaned[0])
xml_train_keys_cleaned = [i.translate(str.maketrans('','', pun)) for i in xml_train_keys_lowered]
print(xml_train_keys_cleaned[0])

# Next we'll clean up the labels

"""
Training Labels
"""
# Build the datasets reading given csv fileand creating dataframe
y_train_labels = pd.read_csv(train_ids
                       ,header = None,sep="\t")
# adding column headings
y_train_labels.columns = ['Id','Party']
# store dataframe into csv file
y_train_labels.to_csv('train_labels_en.csv', 
                index = None)
y_train = y_train_labels['Party'].to_numpy()
print(f'Our training labels are: {y_train}')

"""
Test Labels
"""
# Build the test datasets
y_test = [party_name["valeur"] for party_name in xml_test_values]
print(f'Our test labels are: {y_test}')

"""Add the y_train and x_train to pandas dataframe as well as the y_test and x_test in a separate dataframe."""

train_df = pd.DataFrame(data={"x_train":xml_train_keys_cleaned, "y_train":y_train})
test_df = pd.DataFrame(data={"x_test":xml_test_keys_cleaned, "y_test":y_test})
print(train_df.head())
print(test_df.head())

"""## Conduct some EDA

We have a majorirty of PPE-DE and PSE which suggests that our models may classify the other three poorly depending on the verbosity of the features, therefore we'll shuffle the dataset.

"""

train_df['y_train'].value_counts().plot.bar()

test_df['y_test'].value_counts().plot.bar()

# shuffle the DataFrame rows
train_df = train_df.sample(frac = 1)
test_df = test_df.sample(frac = 1)
# Drop Na
train_df = train_df.dropna()
test_df = test_df.dropna()

# Tokenize via vectorization
train_df["x_train_tokens"] = train_df["x_train"].apply(word_tokenize)
test_df["x_test_tokens"] =   test_df["x_test"].apply(word_tokenize)

# Remove stop words
def remove_stop_words(tokens):
  for token in tokens:
      if token in stopwords.words(LANG):
          tokens.remove(token)
  return tokens
train_df["x_train_cleaned"] = train_df["x_train_tokens"].progress_apply(remove_stop_words)
test_df["x_test_cleaned"] = test_df["x_test_tokens"].progress_apply(remove_stop_words)

"""Let's inspect our cleaned dataset and vectorize using a transformer."""

train_df.head()

test_df.head()

"""# Vectorize with transformer
The paragraphs look pretty good. We can preprocess a bit further as well but  we have applied the basics such as removing stopwords and tokenizing, we'll attempt to get an intial benchmark of the sentence classification using an svc.
"""

# load one of the models listed at https://github.com/MartinoMensio/spacy-sentence-bert/
nlp = spacy_sentence_bert.load_model('en_stsb_distilbert_base')

"""Since we don't have good GPUs we will only sample for the first 5000. Usually we would want to randomly sample to decide."""

# After loading the transformer, we'll vectorize our sentences, it may take a while
"""
We recommend running this on a GPU for faster processing, 
according to TQDM, it should take around 2 Minutes.
"""

# First convert list of strings to strings, to allow for vectorization
# Function to convert 
def list_to_string(s):
   
    # initialize an empty string
    str1 = " "
   
    # return string 
    return (str1.join(s))
train_df["x_train_final"] = train_df["x_train_cleaned"].apply(list_to_string)
test_df["x_test_final"] = test_df["x_test_cleaned"].apply(list_to_string)

# Finally we'll vectorize approx 8 

def vectorize(string):
  return nlp(string).vector
train_df["x_train_vector"] = train_df["x_train_final"].progress_apply(vectorize)
test_df["x_test_vector"] = test_df["x_test_final"].progress_apply(vectorize)

print(type(train_df["x_train_final"][0]))
print(train_df["x_train_final"][0])
train_df.head()

"""## Training the dataset"""

# For each of the features we'll apply 
# Support Vector Machine
clf = SVC(gamma='auto', verbose=True) 
clf.fit(train_df["x_train_vector"].to_list(),train_df["y_train"].to_list())
y_pred = clf.predict(test_df["x_test_vector"].to_list())
print(f'Our accuracy is: {np.round(accuracy_score(test_df["y_test"].to_list(), y_pred)*100, decimals=4)}%')

from sklearn.ensemble import RandomForestClassifier
# For each of the features we'll apply 
# RandomForest
clf = RandomForestClassifier(max_depth=None, random_state=0)
clf.fit(train_df["x_train_vector"].to_list(),train_df["y_train"].to_list())
y_pred = clf.predict(test_df["x_test_vector"].to_list())
print(f'Our accuracy is: {np.round(accuracy_score(test_df["y_test"].to_list(), y_pred)*100, decimals=4)}%')

from sklearn.linear_model import LogisticRegression 
from sklearn.preprocessing import OneHotEncoder

# For each of the features we'll apply 
# LogisticRegression
clf = LogisticRegression(max_iter=5000)
clf.fit(train_df["x_train_vector"].to_list(),train_df["y_train"].to_list())
y_pred = clf.predict(test_df["x_test_vector"].to_list())
print(f'Our accuracy is: {np.round(accuracy_score(test_df["y_test"].to_list(), y_pred)*100, decimals=4)}%')

#from sklearn.naive_bayes import BernoulliNB
from sklearn.naive_bayes import GaussianNB

# For each of the features we'll apply 
# Naive Bayes
clf = GaussianNB()
clf.fit(train_df["x_train_vector"].to_list(),train_df["y_train"].to_list())
y_pred = clf.predict(test_df["x_test_vector"].to_list())
print(f'Our accuracy is: {np.round(accuracy_score(test_df["y_test"].to_list(), y_pred)*100, decimals=4)}%')

"""# Further work

Further work can be accomplished to improve the model such as dimensionality reduction, feature engineering and using better state-of-the-art transformers and larger GPUs.
"""