run:
	streamlit run yokohama-ninka-hoikusho.py

gen-csv:
	nkf -Lu -w --overwrite csv/*.csv
	python gen-location.py
