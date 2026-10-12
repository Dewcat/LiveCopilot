#!/usr/bin/env python3
"""Compile the product owner's reviewed CSV into the offline app snapshot."""
import csv,json,pathlib
root=pathlib.Path(__file__).resolve().parents[2]
rows=list(csv.DictReader((root/'docs/reference/analysis-configurations-2026-10-11.csv').open(encoding='utf-8-sig')))
services={'OpenAI':'separateOpenAI','DeepSeek':'deepSeek','Qwen':'qwen','GLM':'glm','Kimi':'kimi'}
modes={'Off':'disabled','On':'enabled'}
records=[]
for r in rows:
 kind='estimate' if '估算' in r['数据性质'] else 'community' if '产品方' in r['数据性质'] else 'publicSnapshot'
 url=r['速度来源'];source='Artificial Analysis' if 'artificialanalysis.ai' in url else 'OpenRouter' if 'openrouter.ai' in url else 'OpenAI' if 'openai.com' in url else 'Community'
 records.append(dict(id=int(r['编号']),service=services[r['服务商']],model=r['Model ID'],name=r['模型'],thinking=modes.get(r['推理'],r['推理'].lower()),processing=r['处理模式'].lower(),recommended=r['推荐']=='推荐',providerDefault=r['服务商首选']=='是',rank=int(r['全局推荐名次']) if r['全局推荐名次'] else None,reason=r['推荐理由（20字内）'],limits=r['使用建议及限制'],kind=kind,ttft=r['TTFT参考'].removesuffix('s'),speed=r['生成速度参考'].removesuffix(' tok/s'),firstTokenSeconds=float(r['原始TTFT(秒)']) if r['原始TTFT(秒)'] else None,tokensPerSecond=float(r['原始tok/s']) if r['原始tok/s'] else None,currency=r['货币'],input=float(r['输入价/百万']),output=float(r['输出价/百万']),source=source,sourceURL=url if url.startswith('https:') else '',priceURL=r['价格来源'],date='2026-10-10' if '2026-10-10' in r['原始依据'] else '2026-10-11',basis=r['原始依据'],presentation=r['速度数据展示要求']))
assert len(records)==58 and len({(r['model'],r['thinking'],r['processing']) for r in records})==58
assert sum(r['providerDefault'] for r in records)==5
(root/'StealthApp/Resources/AnalysisConfigurations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Imported 58 configurations; originals and provenance preserved.')
