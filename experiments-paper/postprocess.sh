set -e
rm -r csv html
mkdir csv
mkdir html
cd csv
python3 ../../scripts/create_csv.py ../logs 
cd ../html
python3 ../../scripts/create_html.py ../csv ../logs ../../models
echo done