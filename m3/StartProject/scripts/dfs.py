from toposort import toposort, toposort_flatten


print(list(toposort({2: {11},
                9: {11, 8, 10},
                10: {11, 3},
                11: {7, 5},
                8: {7, 3},
               }))
[{3, 5, 7}, {8, 11}, {2, 10}, {9}])