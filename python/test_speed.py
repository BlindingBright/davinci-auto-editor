import time, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fpv_analyzer import FPVAnalyzer
start = time.time()
a = FPVAnalyzer()
results = a.analyze_directory(r'E:\Zoe\SKE Ent\Video\Drone Footage')
elapsed = time.time() - start
print(f'Total time: {elapsed:.1f}s')
for r in results:
    print(f'  {os.path.basename(r["file"])}: {len(r["useful_segments"])} segments -> {r["useful_segments"]}')
