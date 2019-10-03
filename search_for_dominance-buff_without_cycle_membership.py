# William Kavanagh, May 2019
# Extended CSG - Balance chars without a pair with an optimal value above a 'viability threshold'
import re
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import sys, os, datetime
import generate_nd_moves

def find_result(file):
    # Take a log file, return the value found by MCing.
    f = open(file, "r").readlines()
    for i in range(len(f)-1,0,-1):
        if "Result:" in f[i]:
            return f[i].split("ult: ")[1].split(" (value")[0]

def find_opponents(file):
    f = open(file,"r").readlines()
    for line in f:
        if "choose" in line:
            return line.split("_")[1][:-1]

def run(config, output):
    # setup

    print("~~~~~~~~~~~~~~~~")
    chars = ["K","A","W","R","H","M","B","G"]
    full_name = {"K":"Knight","A":"Archer","W":"Wizard",
        "R":"Rogue","H":"Healer","M":"Monk","B":"Barbarian",
        "G":"Gunner"}
    pairs = []
    for i in range(len(chars)):
        for j in range(i+1,len(chars)):
            pairs += [chars[i] + chars[j]]
    results = {}

    for pair in pairs:
        # generate model for pair vs generator

        file_name = pair + "_dominance_check.prism"
        generate_nd_moves.run(pair, config, output+"/"+file_name)
        # Model generated. Now model check.
        os.system("prism " + output + "/" + file_name + " smg.props \
        -prop 1 -exportadvmdp " + output + "/tmp.tra -exportstates " + output + \
        "/tmp.sta -javamaxmem 4g -nopre -maxiters 30000 > " + output + "/log.txt")

        # Find best pair and optimal probability

        print(pair + ":")
        found_opp = find_opponents(output+"/tmp.tra")
        minimax = find_result(output+"/log.txt")
        print("\topposing pair selected as: " + found_opp)
        print("\toptimal probability of: " + minimax + "\n")
        results[pair] = {"res":minimax, "opp":found_opp}

    # Results found for all pairs. Plot results using networkx

    plt.subplots(figsize=(14,14))
    G = nx.DiGraph()
    evil_nodes = []
    good_nodes = []

    for p in results.keys():
        if float(results[p]["res"]) < 0.499 or p != results[p]["opp"]:
            G.add_edge(p, results[p]["opp"], weight= str(round(float(results[p]["res"]),4)))
        else:
            evil_nodes += [p]
            G.add_edge(p, p, weight= 0.5)
    plt.plot()

    if len(evil_nodes) == 0:
        try:
            nx.find_cycle(G)
            if len(nx.find_cycle(G)) > 1:
                for e in nx.find_cycle(G):
                    good_nodes += [e[0]]
        except:
            pass

    colour_list = []
    for n in G.nodes():
        if n in good_nodes or n in evil_nodes:
            colour_list += [0]
        else:
            colour_list += [1]

    carac = pd.DataFrame({'ID':G.nodes(), 'colour_group':colour_list})
    carac= carac.set_index('ID')
    carac=carac.reindex(G.nodes())
    carac['colour_group']=pd.Categorical(carac['colour_group'])
    carac['colour_group'].cat.codes

    edge_labels=dict([((u,v,),d['weight'])
                 for u,v,d in G.edges(data=True)])
    pos = nx.shell_layout(G)
    nx.draw(G, pos, with_labels=True, font_weight='bold', font_size=16,
            node_color=carac['colour_group'].cat.codes, cmap=plt.cm.Set1,
            draw_network_edge_labels = True, node_size=1500,
            arrowsize=25, arrowstyle='-|>', edge_color="blue", width=1.5)

    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=16)
    plt.axis('off')
    plt.title("Optimality Relationship Graph: " + config, fontsize=18)
    plt.savefig("results/graphics/" + config + "_optimality_relationship.png")      # Save graph to file
    print("~~~~~~~~~~~~~~~~")
    return(results, nx.find_cycle(G))

def suggest_balance(res, cyc):
    # Takes a dictionary of results, returns list of chars to buff, nerf and <bool> if a dominant strategy is present.
    # Dominant check
    chars = ["K","A","W","R","H","M","B","G"]
    pairs = res.keys()
    buff = []
    nerf = []
    cycle = []
    for p in pairs:
        if float(res[p]["res"]) > 0.499:           # Dominant pair
            print("Nerfing dominant pair: " + p)
            return [0], p, True
    for c in cyc:
        for x in c[0]:
            if x not in cycle:
                cycle += [x]
    for c in chars:
        if c not in cycle:
            buff += [c]
    print("buffing: " + str(buff))
    return buff, [], False

def enact_balance(file, buff, nerf, dom):
    old = open("configurations/" + file + ".txt", "r").readlines()
    if file[-1].isdigit():                          # Sort file name
        num_string = ""
        for i in range(len(file)-1,-1,-1):
            if file[i].isdigit(): num_string = file[i] + num_string
            else:
                break
        file = file[:-len(num_string)] + str(int(num_string)+1)
    else: file = file + "_1"
    new = open("configurations/" + file + ".txt", "w")  # file name sorted, new file opened for writing.
    for line in old:
        if "accuracy" in line and line[13] in buff:
            cut = line.index(".")
            if float(line[cut:-2]) >= 0.98: return (line[13], False)
            new_line = line[:cut-1] + str(float(line[cut:-2])+.02) + ";\n"
            new.write(new_line)
        elif "accuracy" in line and line[13] in nerf:
            cut = line.index(".")
            if dom:         # if dominant, nerf by 10%
                if float(line[cut:-2]) <= 0.1: return (line[13], False)
                new_line = line[:cut-1] + str(float(line[cut:-2])-.1) + ";\n"
            else:           # if not dominant, but too strong, nerf by 1%
                if float(line[cut:-2]) <= 0.01: return (line[13], False)
                new_line = line[:cut-1] + str(float(line[cut:-2])-.01) + ";\n"
            new.write(new_line)
        else:
            new.write(line)
    return(file,True)

configs = sys.argv[1:]
output = "test_output"
for c in configs:
    print("Analysing for configuration: " + c)
    result, cycle = run(c, output)
    f = open("results/" + c + "-results.txt","w")
    for comp in result: f.write(comp + " countered by: " + result[comp]['opp'] + ", optimal value = " + str(result[comp]["res"]) + "\n")
    f.close()
    buff, nerf, dominant = suggest_balance(result, cycle)
    if len(buff)+len(nerf) > 0:
        file, cont = enact_balance(c, buff, nerf, dominant)
        if cont: configs.append(file)

if len(buff)+ len(nerf) == 0:
    print("Success, balance acheived.")
else:
    print("failure due to " + file + " in " + configs[-1])
