#!/bin/bash
for file in ./configs/ppsn/round0/*; do python ./driver.py --config $file; done

for file in ./configs/ppsn/experiment1/*; do python ./driver.py --config $file; done
# python ./findChampions.py ./logs/science-is-hard/experiment1/*/*/ && \
# python ./globalPerformanceEstimation.py ./logs/science-is-hard/experiment1/*/*/champions.json

# python ./findChampions.py ./logs/ppsn/experiment1/steadystate*/*/ && \
# python  ./globalPerformanceEstimation.py ./logs/ppsn/experiment1/steadystate*/*/champions.json

for file in ./configs/ppsn/experiment2/*; do python ./driver.py --config $file; done
# python ./findChampions.py ./logs/science-is-hard/experiment2/*/*/

for file in ./configs/ppsn/experiment3/*; do python ./driver.py --config $file; done
# python ./findChampions.py ./logs/science-is-hard/experiment3/*/*/

# python ./globalPerformanceEstimation.py ./logs/experiment2/maelstrom_s*/*/champions.json
