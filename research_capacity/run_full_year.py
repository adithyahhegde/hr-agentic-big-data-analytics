import os, json, math
from pathlib import Path
import duckdb, numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

OUT=Path('research_capacity/results'); OUT.mkdir(parents=True,exist_ok=True)
YEAR=2024
urls=[f'https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{YEAR}-{m:02d}.parquet' for m in range(1,13)]
con=duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs")
# Aggregate month-by-month so raw trip files never need to be stored locally.
parts=[]
for i,u in enumerate(urls,1):
    print(f'[{i}/12] {u}',flush=True)
    q="""SELECT date_trunc('hour', tpep_pickup_datetime) AS hour, PULocationID, count(*)::INTEGER AS demand FROM read_parquet(?) WHERE PULocationID IS NOT NULL GROUP BY 1,2"""
    parts.append(con.execute(q,[u]).df())
hourly=pd.concat(parts,ignore_index=True).groupby(['hour','PULocationID'],as_index=False).demand.sum()
hourly.to_csv(OUT/'hourly_demand_2024.csv',index=False)

start=hourly.hour.min(); end=hourly.hour.max(); cut1=start+(end-start)*.60; cut2=start+(end-start)*.80
top=hourly[hourly.hour<cut1].groupby('PULocationID').demand.sum().nlargest(20).index.tolist()
models={
 'Ridge':Ridge(alpha=10),
 'Random Forest':RandomForestRegressor(n_estimators=100,random_state=42,n_jobs=-1,min_samples_leaf=2),
 'XGBoost':XGBRegressor(n_estimators=300,max_depth=6,learning_rate=.05,subsample=.9,colsample_bytree=.9,objective='reg:squarederror',random_state=42,n_jobs=-1)
}
def smape(y,p):
 d=np.abs(y)+np.abs(p); return np.mean(np.where(d==0,0,2*np.abs(y-p)/d))*100
val=[]; test=[]; preds=[]
for zone in top:
 z=hourly[hourly.PULocationID==zone][['hour','demand']].copy().set_index('hour').reindex(pd.date_range(start.floor('h'),end.ceil('h'),freq='h'),fill_value=0).rename_axis('hour').reset_index()
 z['hour_of_day']=z.hour.dt.hour; z['dow']=z.hour.dt.dayofweek; z['month']=z.hour.dt.month; z['weekend']=(z.dow>=5).astype(int)
 for lag in [1,2,24,48,168]: z[f'lag{lag}']=z.demand.shift(lag)
 z['roll24']=z.demand.shift(1).rolling(24).mean(); z=z.dropna()
 n=len(z); a=int(.6*n); b=int(.8*n); tr,va,te=z.iloc[:a],z.iloc[a:b],z.iloc[b:]
 f=['hour_of_day','dow','month','weekend','lag1','lag2','lag24','lag48','lag168','roll24']
 pv=va.lag168.values; val.append({'zone':zone,'model':'Seasonal Naive','MAE':mean_absolute_error(va.demand,pv),'RMSE':mean_squared_error(va.demand,pv)**.5,'sMAPE':smape(va.demand.values,pv)})
 for name,t in models.items():
  m=t.__class__(**t.get_params()); m.fit(tr[f],tr.demand); p=m.predict(va[f]); val.append({'zone':zone,'model':name,'MAE':mean_absolute_error(va.demand,p),'RMSE':mean_squared_error(va.demand,p)**.5,'sMAPE':smape(va.demand.values,p)})
 tv=pd.concat([tr,va])
 for name,t in models.items():
  m=t.__class__(**t.get_params()); m.fit(tv[f],tv.demand); p=m.predict(te[f]); test.append({'zone':zone,'model':name,'MAE':mean_absolute_error(te.demand,p),'RMSE':mean_squared_error(te.demand,p)**.5,'sMAPE':smape(te.demand.values,p)}); preds.append(pd.DataFrame({'hour':te.hour.values,'zone':zone,'actual':te.demand.values,'model':name,'forecast':p}))
 preds.append(pd.DataFrame({'hour':te.hour.values,'zone':zone,'actual':te.demand.values,'model':'Seasonal Naive','forecast':te.lag168.values}))
val=pd.DataFrame(val); test=pd.DataFrame(test); pred=pd.concat(preds,ignore_index=True)
val.to_csv(OUT/'validation_accuracy_2024.csv',index=False); test.to_csv(OUT/'test_forecast_accuracy_2024.csv',index=False); pred.to_csv(OUT/'test_predictions_2024.csv',index=False)
rows=[]
for model,g in pred.groupby('model'):
 for beta in [0,.1,.2,.3]:
  cap=np.ceil(np.maximum(g.forecast.values,0)*(1+beta)); under=np.maximum(g.actual.values-cap,0); over=np.maximum(cap-g.actual.values,0)
  for r in [1,3,5,10]: rows.append({'model':model,'buffer':beta,'under_over_ratio':r,'mean_cost':np.mean(r*under+over),'under_rate':np.mean(under>0),'mean_under':under.mean(),'mean_over':over.mean()})
ops=pd.DataFrame(rows); ops.to_csv(OUT/'operational_sensitivity_2024.csv',index=False)
summary={'months':12,'zones':20,'validation_mean':val.groupby('model')[['MAE','RMSE','sMAPE']].mean().round(4).to_dict('index'),'test_mean':test.groupby('model')[['MAE','RMSE','sMAPE']].mean().round(4).to_dict('index'),'best_operational':ops.loc[ops.groupby(['model','under_over_ratio']).mean_cost.idxmin()].to_dict('records')}
(OUT/'full_year_summary.json').write_text(json.dumps(summary,indent=2,default=float)); print(json.dumps(summary,indent=2,default=float))
