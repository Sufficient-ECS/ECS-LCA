This example repdouces [this example](https://github.com/brightway-lca/bw_timex/blob/main/notebooks/examples/electric_vehicle_premise.ipynb) from bw_timex.

Run
```
./scripts/treat_foreground.py      ./examples/bw_timex/foreground.yaml \
                                -s ./examples/bw_timex/scenarios.txt \
                                -m ./examples/bw_timex/method_list.txt \
                                -c ./examples/bw_timex/custom

./examples/bw_timex/graph.py
```

The graph should be in [./results/bw_timex_example.pdf](../../results/bw_timex_example.pdf)

There is a little difference in the graphs. It seems concentrated around the production. The source might be modified activities.