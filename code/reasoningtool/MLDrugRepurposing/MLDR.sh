#!/bin/bash

###################################
##### Variable Initialization #####
###################################

# This is the command you use to run python scripts. Most likely "python" or "python3"
py_name="python"

# This is the path to the gzipped semmeddb predication sql dump. You do not need to unzip.
semmed="data/semmedVER31_R_PREDICATION_to12312017.sql.gz"

# This is the username and password for the neo4j instance you are using to host the graph. By default the username and password are both "neo4j"
neo4j_user="neo4j"
neo4j_pass="neo4j"
neo4j_url="bolt://localhost:7687"

# This is the path to node2vec. download and install from here: https://github.com/snap-stanford/snap/tree/master/examples/node2vec
# Make sure that you run the makefile before tryig to use
node2vec_path="/home/womackf/Dropbox/pyUMLS/snap/snap-master/examples/node2vec/node2vec"

# There are the parameters used in the EMB file creation. Descriptions are listed here: https://github.com/snap-stanford/snap/tree/master/examples/node2vec
PVAR="1"
QVAR="5"
EVAR="5"
DVAR="256"
LVAR="128"
RVAR="15"

# This is the minimum number on entries in SemMedDB needed for a realationship to be considered a ground truth. (Higher numbers cut out noise but at the cost of a smaller training set)
cutoff="5"

# This indicates if you want a roc curve plotted for the end model (True for yes and False for no)
roc="True"

# This indicates if you want to plot the precentage of treat predictions for random drug-disease pairs at different cutoffs
rand_plot="False"

# This is the maximum depth each tree and the number of trees in the random forest model
trees="1000"
depth="15"

# This is that name of the file you wish to save the model as
model_file="data/RandomForestModel.pkl"

# This indicates the type of model you wish to use (RF - randomforest and LR - logistic regression)
type="RF"

# The name of the csv you wish to import to predict on
data_file="data/test_set.csv"

################
##### Code #####
################

# This section converts the gzipped mysql dump from SemMedDB to a csv
echo "Converting SemMedDB to csv..."
eval "zcat ${semmed} | ${py_name} mysqldump_to_csv.py"

# This section extracts, counts, and formats positive training data from SemMEdDB
echo "Extracting positives from SemMedDB..."
echo "pmid,relationship,subject_cui,subject_name,object_cui,object_name" > data/to_split.csv
grep ',TREATS,' PREDICATION.csv | csvcut -c=3,4,5,6,9,10 >> data/to_split.csv
eval "${py_name} SplitRel.py --f data/to_split.csv --s data/split.csv"
rm data/to_split.csv
echo "count,source,target" > data/semmed_tp.csv
tail -n+2 data/split.csv | csvcut -c=3,5 | sort | uniq --count | sed 's/^ *//g' | sed 's/ /,/g' >> data/semmed_tp.csv
rm data/split.csv

# This section extracts, counts, and formats negative training data from SemMEdDB
echo "Extracting negatives from SemMedDB..."
echo "pmid,relationship,subject_cui,subject_name,object_cui,object_name" > data/to_split.csv
grep ',NEG_TREATS,' PREDICATION.csv | csvcut -c=3,4,5,6,9,10 >> data/to_split.csv
eval "${py_name} SplitRel.py --f data/to_split.csv --s data/split.csv"
rm data/to_split.csv
echo "count,source,target" > data/semmed_tn.csv
tail -n+2 data/split.csv | csvcut -c=3,5 | sort | uniq --count | sed 's/^ *//g' | sed 's/ /,/g' >> data/semmed_tn.csv
rm data/split.csv

mv PREDICATION.csv data/

# This section downloads the graph and nodes needed for cui -> curie mapping
echo "Downloading graph..."
eval "${py_name} PullGraph.py --user ${neo4j_user} --password ${neo4j_pass} --url ${neo4j_url}"

# This section Creates a cui -> curie map file.
# NOTE: This will only work if a couple of services are running on our aws instances
# if you do not know if those are running simply do not uncomment this line and download the pre-
# generated file on out github.
#eval "${py_name} BuildCuiMap.py --source data/drugs.csv --target data/diseases.csv"

# This section formats the graph for ingestion by node2vec and passes it to node2vec to create vectorizations of our nodes
echo "Converting graph to edgelist..."
eval "${py_name} EdgelistMaker.py"
eval "${node2vec_path} -i:${PWD}/data/rel.edgelist -o:${PWD}/data/graph.emb -q:${QVAR} -p:${PVAR} -e:${EVAR} -d:${DVAR} -l:${LVAR} -r:${RVAR} -v -dr"


# This section downloads the mychem training data
echo "Downloading MyChem data..."
eval "${py_name} MyChemGT.py"

# This section converts the training data csvs from cuis to curie ids
echo "Converting cuis to curie ids..."
eval "${py_name} ConvertCsv.py --tp data/semmed_tp.csv --tn data/semmed_tn.csv"
eval "${py_name} ConvertCsv.py --tp data/mychem_tp_umls.csv --tn data/mychem_tn_umls.csv -t True"

# This section builds a model using logistic regression and save it to the file LogReg.pkl for prediction using Pred.py
echo "Building model..."
eval "${py_name} LogReg.py --tp data/semmed_tp.csv data/mychem_tp.csv data/mychem_tp_umls.csv data/ndf_tp.csv \\
                           --tn data/semmed_tn.csv data/mychem_tn.csv data/mychem_tn_umls.csv data/ndf_tn.csv \\
                           --emb data/graph.emb \\
                           --map data/map.csv \\
                           -c ${cutoff} \\
                           --roc ${roc} \\
                           --rand ${rand_plot} \\
                           --save ${model_file} \\
                           --depth ${depth} \\
                           --trees ${trees} \\
                           --type ${type}"


##### Uncomment to make predictions ######
# This section makes predictions and then saves them to a csv
#echo "Making predictions..."
#eval "${py_name} predictor.py --emb data/graph.emb \\
#                              --model ${model_file} \\
#                              --map data/map.csv \\
#                              --data ${data_file} \\
#                              --save data/prediction.csv"

