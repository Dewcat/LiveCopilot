import copy, unittest
from audit_laya_full_audio import audit_rows

def evidence():
    original=[dict(id=str(i),text=('问' if i%2 else 'request')+str(i),respond=i<80,context={}) for i in range(160)]
    captions=[dict(id=c['id'],spoken=c['text'],text=c['text'].upper(),respond=c['respond'],context=c['context']) for c in original]
    rows=[]
    for c in captions:
        r=dict(id=c['id'],expected=c['respond'],spoken=c['spoken'],asr=c['text'])
        for f in ['spoken','asr','asr_long']:
            r.update({f+'_score':.9 if c['respond'] else .1,f+'_passed':True,f+'_tokens':1000 if f=='asr_long' else 140})
        rows.append(r)
    summary=dict(positive=80,negative=80,missed_requests=0,false_triggers=0,recall=1.,false_positive_rate=0.)
    report=dict(threshold=.8,total=160,rows=rows,spoken_passed=160,asr_passed=160,summaries={f:copy.deepcopy(summary) for f in ['spoken','asr','asr_long']})
    return report,captions,original

class FullAudioAuditTests(unittest.TestCase):
    def test_per_context_gate_cannot_be_hidden_by_total_accuracy(self):
        report,captions,original=evidence()
        for r in report['rows'][:5]:r['asr_long_score']=.1;r['asr_long_passed']=False
        report['summaries']['asr_long'].update(missed_requests=5,recall=75/80)
        result=audit_rows(report,captions,original)
        self.assertFalse(result['full_audio_gate_passed'])
        self.assertTrue(result['gates']['asr'])

    def test_exact_95_percent_is_allowed_without_requiring_160(self):
        report,captions,original=evidence()
        for r in report['rows'][:4]:r['asr_long_score']=.1;r['asr_long_passed']=False
        for r in report['rows'][80:84]:r['asr_long_score']=.9;r['asr_long_passed']=False
        report['summaries']['asr_long'].update(missed_requests=4,false_triggers=4,recall=.95,false_positive_rate=.05)
        self.assertTrue(audit_rows(report,captions,original)['full_audio_gate_passed'])

    def test_rejects_exclusion_relabeling_short_context_and_invalid_scores(self):
        for mutation in ['missing','duplicate','label','tokens','nonfinite','summary','text','context']:
            with self.subTest(mutation=mutation):
                report,captions,original=evidence()
                if mutation=='missing':report['rows'].pop()
                elif mutation=='duplicate':report['rows'][-1]=report['rows'][0]
                elif mutation=='label':report['rows'][0]['expected']=False
                elif mutation=='tokens':report['rows'][0]['asr_long_tokens']=500
                elif mutation=='nonfinite':report['rows'][0]['asr_score']=float('nan')
                elif mutation=='summary':report['summaries']['asr']['recall']=.9
                elif mutation=='text':report['rows'][0]['asr']='corrected transcript'
                else:captions[0]['context']={'changed':True}
                with self.assertRaises(ValueError):audit_rows(report,captions,original)

if __name__=='__main__':unittest.main()
