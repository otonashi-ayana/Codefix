import matplotlib.pyplot as plt

def plot_sales(summary):
    plt.bar(summary["region"], summary["sales"])
    plt.title("Sales Summary")
    plt.xlabel("Region")
    plt.ylabel("Sales")
    plt.show()