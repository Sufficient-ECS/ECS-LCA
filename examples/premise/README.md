This example repdouces [this graph](https://raw.githubusercontent.com/polca/premise/7464b39c96906640bc8f8186d0456d2bb7b69f8d/examples/example_superDB.png) from the [examples.ipynb](https://github.com/polca/premise/blob/master/examples/examples.ipynb) file from premise.


Then, run
```
 ./scripts/treat_foreground.py ./examples/premise/foreground.yaml -s ./examples/premise/scenarios.txt -m ./examples/premise/methods.txt

 ./examples/premise/graph.py
```

The graph should be in [./results/premise_example.pdf](../../results/premise_example.pdf)

Slight difference should be due to ecoinvent version.

Note that premise has only been successfully tested with ecoinvent 3.11.
3.7 and 3.8 led to a crash without clear cause.