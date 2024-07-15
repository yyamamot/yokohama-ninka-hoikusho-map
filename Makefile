run:
	streamlit run yokohama-ninka-hoikusho.py

gen-csv:
	nkf --guess -Lu -w csv/*.csv
	python gen-location.py
