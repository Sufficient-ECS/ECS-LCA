This example repdouces [this example](https://github.com/brightway-lca/bw_timex/blob/d9653d82083889ce9749a0d5c1e05d93dadf41d1/notebooks/case_studies/electric_vehicle_premise.ipynb) from bw_timex.

Run
```
uv run treat_foreground         ./examples/bw_timex/foreground.yaml \
                                -t ./examples/bw_timex/scenarios_list.txt \
                                -p ./examples/bw_timex/scenarios_list.txt \
                                -m ./examples/bw_timex/method_list.txt \
                                -c ./examples/bw_timex/custom

./examples/bw_timex/graph.py
```

The graph should be in [./results/bw_timex_example.pdf](../../results/bw_timex_example.pdf)

There is a little difference in the graphs. It seems concentrated around the production. The source might be modified activities.