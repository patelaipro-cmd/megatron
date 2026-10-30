#!/usr/bin/env node
/*
 * EXP-014 : premier cycle experimental de Poisson a forces d'equipes.
 * Source : data/matches_top5_2020-2026.csv au SHA Git blob indique.
 * Aucune connexion reseau, aucune ecriture du modele, aucun GO.
 * Executer : node exp014_train.js data/matches_top5_2020-2026.csv [resultats.json] [checkpoint.json]
 * ATTENTION : test 2025-26 deja exploite dans le projet, PAS un test prospectif.
 */
'use strict';
const fs=require('node:fs'), crypto=require('node:crypto'), path=require('node:path');
const SOURCE_BLOB_SHA='0bdc03ab503c4f8020e50e66513c74b84d51ad68';
const CUT_TRAIN='2024-07-01',CUT_VAL='2025-07-01',CUT_TEST='2026-07-01';
const RIDGE=[0.002,0.02,0.10];

function parseSource(content){
  const lines=content.trim().split(/\r?\n/),header=lines.shift().split(',');
  for(const c of ['Division','MatchDate','HomeTeam','AwayTeam','FTHome','FTAway']){
    if(!header.includes(c))throw Error(`Colonne absente: ${c}`);
  }
  const out=[];
  for(const [i,line] of lines.entries()){
    const z=line.split(',');
    if(z.length!==header.length)throw Error(`CSV avec virgule/colonnes inattendues ligne ${i+2} : ${z.length}`);
    const at=Object.fromEntries(header.map((key,j)=>[key,z[j]]));
    const hg=+at.FTHome,ag=+at.FTAway;
    if(!/^\d{4}-\d\d-\d\d$/.test(at.MatchDate) || !Number.isInteger(hg)||!Number.isInteger(ag)||hg<0||ag<0)
      throw Error(`Date ou score invalide ligne ${i+2}`);
    out.push({league:at.Division,date:at.MatchDate,home:at.HomeTeam,away:at.AwayTeam,hg,ag});
  }
  return out;
}
function trainModel(data,reg){
 const m={reg,att:{},def:{},hl:{},al:{},avg:{}},sums={};
 for(const x of data){let z=sums[x.league]??={sh:0,sa:0,n:0};z.sh+=x.hg;z.sa+=x.ag;z.n++;}
 for(let [lg,z] of Object.entries(sums)){m.hl[lg]=Math.log(z.sh/z.n);m.al[lg]=Math.log(z.sa/z.n);m.avg[lg]=[z.sh/z.n,z.sa/z.n]}
 const n=data.length;
 let order=Array.from({length:n},(_,i)=>i),seed=17;
 function rand(){seed=(Math.imul(1664525,seed)+1013904223)>>>0;return seed/4294967296}
 for(let epoch=0;epoch<32;epoch++){
  for(let i=n-1;i>0;i--){let j=Math.floor(rand()*(i+1));[order[i],order[j]]=[order[j],order[i]]}
  let lr=0.014/(1+epoch*0.18);
  for(const id of order){
   const x=data[id],lg=x.league,hk=lg+'|'+x.home,ak=lg+'|'+x.away;
   let ah=m.att[hk]??0,aa=m.att[ak]??0,dh=m.def[hk]??0,da=m.def[ak]??0;
   let lh=Math.exp(Math.max(-1.5,Math.min(2.8,m.hl[lg]+ah-da)));
   let la=Math.exp(Math.max(-1.5,Math.min(2.8,m.al[lg]+aa-dh)));
   let eh=Math.max(-5,Math.min(5,x.hg-lh)),ea=Math.max(-5,Math.min(5,x.ag-la));
   m.hl[lg]+=lr*eh*0.15;m.al[lg]+=lr*ea*0.15;
   m.att[hk]=Math.max(-1.5,Math.min(1.5,ah+lr*(eh-reg*ah)));
   m.att[ak]=Math.max(-1.5,Math.min(1.5,aa+lr*(ea-reg*aa)));
   m.def[hk]=Math.max(-1.5,Math.min(1.5,dh+lr*(-ea-reg*dh)));
   m.def[ak]=Math.max(-1.5,Math.min(1.5,da+lr*(-eh-reg*da)));
  }
 }
 return m;
}
function rates(m,x){let lg=x.league,hk=lg+'|'+x.home,ak=lg+'|'+x.away;
 return [Math.exp(Math.max(-1.5,Math.min(2.8,(m.hl[lg]??Math.log(1.4))+(m.att[hk]??0)-(m.def[ak]??0)))),Math.exp(Math.max(-1.5,Math.min(2.8,(m.al[lg]??Math.log(1.1))+(m.att[ak]??0)-(m.def[hk]??0))))];
}
function poisson(x){let p=[Math.exp(-x)];for(let i=1;i<=12;i++)p.push(p[i-1]*x/i);return p;}
function probs(a,b){let p=poisson(a),q=poisson(b),out={H:[0,0,0],A:[0,0,0],D:0},sum=0;
for(let i=0;i<p.length;i++)for(let j=0;j<q.length;j++){let v=p[i]*q[j];sum+=v;let d=i-j;if(d===0)out.D+=v;if(d>=1)out.H[0]+=v;if(d>=2)out.H[1]+=v;if(d>=3)out.H[2]+=v;if(d<=-1)out.A[0]+=v;if(d<=-2)out.A[1]+=v;if(d<=-3)out.A[2]+=v;}for(let k of ['H','A'])out[k]=out[k].map(v=>v/sum);out.D/=sum;return out;
}
function assess(m,set){let totals={n:0,loss:[0,0,0],brier:[0,0,0],baseloss:[0,0,0],basebrier:[0,0,0],pred:[0,0,0],observed:[0,0,0]},perLg={};
for(const x of set){
 const [a,b]=rates(m,x),p=probs(a,b),fav=p.H[0]>=p.A[0]?'H':'A',y=fav==='H'?x.hg-x.ag:x.ag-x.hg;
 const [bh,ba]=m.avg[x.league]??[1.45,1.1],base=probs(bh,ba);
 const t=perLg[x.league]??={n:0,loss:0,baseline:0};t.n++;
 for(let k=0;k<3;k++){
   const v=Math.max(.000001,Math.min(.999999,p[fav][k])),u=Math.max(.000001,Math.min(.999999,base[fav][k])),event= +(y>=k+1);
   const logloss=-(event*Math.log(v)+(1-event)*Math.log(1-v));
   const bsloss=-(event*Math.log(u)+(1-event)*Math.log(1-u));
   totals.loss[k]+=logloss;totals.baseloss[k]+=bsloss;totals.brier[k]+=(v-event)**2;totals.basebrier[k]+=(u-event)**2;totals.pred[k]+=v;totals.observed[k]+=event;t.loss+=logloss;t.baseline+=bsloss;
 }totals.n++;
}const n=totals.n;
return {n,logloss:totals.loss.map(v=>v/n),baseline_logloss:totals.baseloss.map(v=>v/n),brier:totals.brier.map(v=>v/n),baseline_brier:totals.basebrier.map(v=>v/n),p_mean:totals.pred.map(v=>v/n),observed:totals.observed.map(v=>v/n),per_league:Object.fromEntries(Object.entries(perLg).map(([lg,v])=>[lg,{n:v.n,ll:v.loss/(3*v.n),baseline:v.baseline/(3*v.n)}]))};
}
function run(records,sourceSha){
 const train=records.filter(x=>x.date<CUT_TRAIN),val=records.filter(x=>x.date>=CUT_TRAIN&&x.date<CUT_VAL),test=records.filter(x=>x.date>=CUT_VAL&&x.date<CUT_TEST);
 if(train.length<1000||val.length<200||test.length<200)throw Error('Jeu trop petit / repartition temporelle anormale');
 const trials=RIDGE.map(reg=>{let m=trainModel(train,reg),r=assess(m,val);return {reg,val:r}});
 const ranked=[...trials].sort((a,b)=>a.val.logloss.reduce((p,x)=>p+x,0)-b.val.logloss.reduce((p,x)=>p+x,0));
 const chosen=ranked[0].reg,finalModel=trainModel(train.concat(val),chosen),holdout=assess(finalModel,test);
 return {experience:'EXP-014-pilot-poisson-team-strength',source_blob_sha:sourceSha,source:'data/matches_top5_2020-2026.csv',intervalles:{train:train.length,validation:val.length,test:test.length},seuils:{train_avant:CUT_TRAIN,validation_avant:CUT_VAL,test_avant:CUT_TEST},parametres:{epochs:32,reg_candidates:RIDGE,selected_reg:chosen,seed:17},validation:trials.map(o=>({ridge:o.reg,n:o.val.n,logloss:o.val.logloss,baseline:o.val.baseline_logloss})),holdout,teams:Object.keys(finalModel.att).length,decision:'EXPERIMENTAL_NON_DEPLOYABLE',limites:['Test retrospecif 2025-26 deja utilise dans le projet','Aucune preuve prospective de performance','Scores championnat uniquement, pas de coupes ni absences','Comparaison contre une baseline simple, pas contre le MEGATRON existant','Entrainement isole, aucune ecriture du depot ni de modele de production']};
}
function main(){
 const source=process.argv[2]; if(!source)throw Error('Usage: node exp014_train.js <data/matches_top5_2020-2026.csv> [resultats.json]');
 const buffer=fs.readFileSync(source),sha=crypto.createHash('sha1').update(`blob ${buffer.length}\0`).update(buffer).digest('hex');
 if(sha!==SOURCE_BLOB_SHA)throw Error(`SHA Git blob inattendu ${sha}, attendu ${SOURCE_BLOB_SHA} : arret anti-derive`);
 const records=parseSource(buffer.toString('utf8'));
 const output=run(records,sha);
 if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(output,null,2)+'\n');
 if(process.argv[4]){
   const training=records.filter(x=>x.date<CUT_VAL);
   const m=trainModel(training,output.parametres.selected_reg);
   const checkpoint={experience:output.experience,source_blob_sha:sha,entrainement_avant:CUT_VAL,reg:m.reg,intercept_domicile:m.hl,intercept_exterieur:m.al,attaque:m.att,defense:m.def,moyennes_ligues:m.avg,statut:'EXPERIMENTAL_NON_DEPLOYABLE'};
   fs.writeFileSync(process.argv[4],JSON.stringify(checkpoint,null,2)+'\n');
 }
 process.stdout.write(JSON.stringify(output,null,2)+'\n');
}
if(require.main===module)main();
module.exports={parseSource,trainModel,rates,poisson,probs,assess,run};
