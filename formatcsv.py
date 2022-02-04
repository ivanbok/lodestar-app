import pandas as pd

df = pd.read_csv("DSO_database.csv")

## Convert DEC string to FLOAT
df['DEC'] = df['DEC'].str.strip()
df['DEC_deg'] = df['DEC'].str.split().str[0]
df['DEC_deg'] = pd.to_numeric(df['DEC_deg'])
df['DEC_min'] = df['DEC'].str.split().str[1]
df['DEC_min'] = pd.to_numeric(df['DEC_min'])
df['DEC_min'] = df['DEC_min'] / 60
df['DEC'] = df['DEC_deg'] + df['DEC_min']
df = df.drop(['DEC_deg', 'DEC_min'], axis=1)

## Convert RA string to FLOAT
df['RA'] = df['RA'].str.strip()
df['RA_h'] = df['RA'].str.split().str[0]
df['RA_h'] = pd.to_numeric(df['RA_h'])
df['RA_min'] = df['RA'].str.split().str[1]
df['RA_min'] = pd.to_numeric(df['RA_min'])
df['RA_min'] = df['RA_min'] / 60
df['RA'] = df['RA_h'] + df['RA_min']
df = df.drop(['RA_h', 'RA_min'], axis=1)

df.to_csv('DSO_database.csv')