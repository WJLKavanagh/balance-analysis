
def rename(file):
    if file[-1].isdigit():
        num_string = ""
        for i in range(len(file)-1,-1,-1):
            if file[i].isdigit(): num_string = file[i] + num_string
            else:
                break
        file = file[:-len(num_string)] + str(int(num_string)+1)
    else: file = file + "_1"
    print(file)

rename("beta_9")
rename("beta_13")
