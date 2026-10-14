"""COL2010 Homework 3 setup: deterministic clustering datasets.

Running this file creates ``module3_data.npz`` and ``visualization.py``.
It also downloads and caches the small real-world datasets used in the
Clustering Laboratory.  scikit-learn is deliberately not used anywhere.
"""
from __future__ import annotations

import csv
import io
import os
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np

DATA_FILENAME = "module3_data.npz"
CACHE_DIR = Path("module3_real_data")

URLS = {
    "iris": "https://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data",
    "wine": "https://archive.ics.uci.edu/ml/machine-learning-databases/wine/wine.data",
    "penguins": "https://raw.githubusercontent.com/allisonhorst/palmerpenguins/main/inst/extdata/penguins.csv",
    "wholesale": "https://archive.ics.uci.edu/ml/machine-learning-databases/00292/Wholesale%20customers%20data.csv",
    "digits_train": "https://archive.ics.uci.edu/ml/machine-learning-databases/optdigits/optdigits.tra",
}


def _blob(rng, mean, cov, n):
    return rng.multivariate_normal(np.asarray(mean, float), np.asarray(cov, float), n)


def _standardize(X):
    X = np.asarray(X, float)
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd


def _download_text(name: str, url: str) -> str:
    """Download once, then reuse a local cached copy."""
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{name}.csv"
    if path.exists():
        return path.read_text(encoding="utf-8")
    req = Request(url, headers={"User-Agent": "COL2010-HW3/1.0"})
    try:
        with urlopen(req, timeout=30) as response:
            text = response.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(
            f"Could not download {name} from {url}. Run setup.py once with an internet "
            "connection, or ask the instructor for the generated module3_data.npz file."
        ) from exc
    path.write_text(text, encoding="utf-8")
    return text


def _load_iris():
    text = _download_text("iris", URLS["iris"])
    X, y = [], []
    names = {"Iris-setosa": 0, "Iris-versicolor": 1, "Iris-virginica": 2}
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 5:
            continue
        X.append([float(v) for v in row[:4]])
        y.append(names[row[4]])
    X = np.asarray(X, float)
    return X, _standardize(X), np.asarray(y, int)


def _load_wine():
    text = _download_text("wine", URLS["wine"])
    X, y = [], []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 14:
            continue
        y.append(int(row[0]) - 1)
        X.append([float(v) for v in row[1:]])
    X = np.asarray(X, float)
    return X, _standardize(X), np.asarray(y, int)


def _load_penguins():
    text = _download_text("penguins", URLS["penguins"])
    reader = csv.DictReader(io.StringIO(text))
    species_map = {"Adelie": 0, "Chinstrap": 1, "Gentoo": 2}
    fields = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    X, y = [], []
    for row in reader:
        if row.get("species") not in species_map:
            continue
        vals = [row.get(f, "") for f in fields]
        if any(v in ("", "NA", "nan", None) for v in vals):
            continue
        X.append([float(v) for v in vals])
        y.append(species_map[row["species"]])
    X = np.asarray(X, float)
    return X, _standardize(X), np.asarray(y, int)


def _load_wholesale():
    text = _download_text("wholesale", URLS["wholesale"])
    reader = csv.DictReader(io.StringIO(text))
    fields = ["Fresh", "Milk", "Grocery", "Frozen", "Detergents_Paper", "Delicassen"]
    X, channel = [], []
    for row in reader:
        X.append([float(row[f]) for f in fields])
        channel.append(int(row["Channel"]) - 1)
    X = np.asarray(X, float)
    # Spending is highly skewed. We retain raw values and provide a standardized
    # log1p representation for the main clustering laboratory.
    X_log_scaled = _standardize(np.log1p(X))
    return X, X_log_scaled, np.asarray(channel, int)


def _load_digits(max_per_class: int = 70):
    """UCI Optical Recognition digits: 64 pixel features + class label."""
    text = _download_text("digits_train", URLS["digits_train"])
    by_class = {k: [] for k in range(5)}
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 65:
            continue
        label = int(row[-1])
        if label in by_class and len(by_class[label]) < max_per_class:
            by_class[label].append([float(v) for v in row[:-1]])
    X, y = [], []
    for label in range(5):
        X.extend(by_class[label])
        y.extend([label] * len(by_class[label]))
    X = np.asarray(X, float)
    # Pixel values share a common scale; standardize featurewise for PCA/clustering.
    return X, _standardize(X), np.asarray(y, int)


def _balanced_subsample(rng, X, y, max_n=180):
    """Deterministic compact subset so from-scratch O(N^2)/O(N^3) methods remain usable."""
    if len(X) <= max_n:
        return X, y
    classes = np.unique(y)
    per = max_n // len(classes)
    idx = []
    for c in classes:
        cand = np.where(y == c)[0]
        take = min(per, len(cand))
        idx.extend(rng.choice(cand, take, replace=False).tolist())
    idx = np.asarray(idx, int)
    rng.shuffle(idx)
    return X[idx], y[idx]


def _write_visualization_helper(path: str = "visualization.py") -> None:
    Path(path).write_text('"""Supplied plotting and visualization helpers for COL2010 Homework 3."""\nfrom __future__ import annotations\nimport numpy as np\nimport matplotlib.pyplot as plt\n\ndef plot_clusters(X_2d, labels, title="Clustering", ax=None, noise_label=-1):\n    X_2d=np.asarray(X_2d); labels=np.asarray(labels)\n    if X_2d.ndim!=2 or X_2d.shape[1]!=2: raise ValueError("X_2d must have shape (N, 2)")\n    if ax is None: _,ax=plt.subplots(figsize=(5,4))\n    for lab in np.unique(labels):\n        mask=labels==lab; marker="x" if lab==noise_label else "o"; name="noise" if lab==noise_label else f"cluster {lab}"\n        ax.scatter(X_2d[mask,0],X_2d[mask,1],s=24,marker=marker,label=name)\n    ax.set_title(title); ax.set_xlabel("coordinate 1"); ax.set_ylabel("coordinate 2"); ax.legend(fontsize=8); return ax\n\ndef compare_clusterings(X_2d,label_sets,title=None):\n    names=list(label_sets.keys()); fig,axes=plt.subplots(1,len(names),figsize=(4.2*len(names),3.8),squeeze=False)\n    for ax,name in zip(axes[0],names): plot_clusters(X_2d,label_sets[name],name,ax=ax)\n    if title: fig.suptitle(title)\n    fig.tight_layout(); return fig,axes\n\ndef show_digit_examples(X,true_labels=None,cluster_labels=None,n=12,image_shape=(8,8)):\n    X=np.asarray(X); n=min(int(n),len(X)); cols=min(6,n); rows=int(np.ceil(n/cols)); fig,axes=plt.subplots(rows,cols,figsize=(2*cols,2*rows),squeeze=False)\n    for i,ax in enumerate(axes.ravel()):\n        ax.axis("off")\n        if i>=n: continue\n        ax.imshow(X[i].reshape(image_shape),cmap="gray_r"); bits=[]\n        if true_labels is not None: bits.append(f"true={true_labels[i]}")\n        if cluster_labels is not None: bits.append(f"cluster={cluster_labels[i]}")\n        ax.set_title(" | ".join(bits),fontsize=8)\n    fig.tight_layout(); return fig,axes\n\ndef _pairwise_sq_dist(X):\n    sq=np.sum(X*X,axis=1); return np.maximum(sq[:,None]+sq[None,:]-2*X@X.T,0.0)\n\ndef compute_tsne_projection(X,perplexity=30.0,n_iters=350,seed=42):\n    """Exact small-data t-SNE helper for visualization only."""\n    X=np.asarray(X,float)\n    if X.ndim!=2 or len(X)<3: raise ValueError("X must be a 2D array with at least three rows")\n    n=len(X); perplexity=float(min(perplexity,max(2.0,(n-1)/3))); Xc=X-X.mean(axis=0)\n    if Xc.shape[1]>30:\n        _,_,Vt=np.linalg.svd(Xc,full_matrices=False); Xc=Xc@Vt[:30].T\n    D=_pairwise_sq_dist(Xc); target=np.log(perplexity); Pcond=np.zeros((n,n),float)\n    for i in range(n):\n        beta=1.0; lo,hi=-np.inf,np.inf; mask=np.arange(n)!=i; Di=D[i,mask]; p=None\n        for _ in range(45):\n            w=np.exp(-Di*beta); p=w/max(w.sum(),np.finfo(float).tiny); H=-np.sum(p*np.log(np.maximum(p,np.finfo(float).tiny)))\n            if abs(H-target)<1e-5: break\n            if H>target: lo=beta; beta=beta*2 if np.isinf(hi) else (beta+hi)/2\n            else: hi=beta; beta=beta/2 if np.isinf(lo) else (beta+lo)/2\n        Pcond[i,mask]=p\n    P=np.maximum((Pcond+Pcond.T)/(2*n),1e-12); rng=np.random.default_rng(seed); Y=rng.normal(0,1e-4,(n,2)); vel=np.zeros_like(Y)\n    for it in range(int(n_iters)):\n        num=1/(1+_pairwise_sq_dist(Y)); np.fill_diagonal(num,0); Q=np.maximum(num/max(num.sum(),np.finfo(float).tiny),1e-12); Puse=P*(4 if it<100 else 1); coeff=(Puse-Q)*num\n        grad=4*np.sum(coeff[:,:,None]*(Y[:,None,:]-Y[None,:,:]),axis=1); mom=.5 if it<100 else .8; vel=mom*vel-200*grad; Y+=vel; Y-=Y.mean(axis=0)\n    return Y\n', encoding="utf-8")

def generate_data(seed: int = 42, file_path: str = DATA_FILENAME) -> None:
    rng = np.random.default_rng(seed)

    # Existing atomic-task data -------------------------------------------------
    a = _blob(rng, [-4, 0], [[.45, .12], [.12, .65]], 120)
    b = _blob(rng, [0, 4], [[.70, -.25], [-.25, .50]], 130)
    c = _blob(rng, [4, -1.5], [[.55, .08], [.08, .85]], 125)
    X_blobs = np.vstack([a, b, c])
    y_blobs = np.r_[np.zeros(len(a), int), np.ones(len(b), int), np.full(len(c), 2, int)]
    p = rng.permutation(len(X_blobs)); X_blobs, y_blobs = X_blobs[p], y_blobs[p]

    z0 = _blob(rng, [-3, 1], [[1.8, 1.2], [1.2, 1.3]], 130)
    z1 = _blob(rng, [2.5, 1.5], [[1.4, -1.0], [-1.0, 1.1]], 130)
    z2 = _blob(rng, [0, -3], [[.9, .2], [.2, .35]], 110)
    X_aniso = np.vstack([z0, z1, z2])
    y_aniso = np.r_[np.zeros(130, int), np.ones(130, int), np.full(110, 2, int)]
    p = rng.permutation(len(X_aniso)); X_aniso, y_aniso = X_aniso[p], y_aniso[p]

    n = 300; t = rng.uniform(0, np.pi, n // 2)
    m1 = np.c_[np.cos(t), np.sin(t)]; m2 = np.c_[1 - np.cos(t), .5 - np.sin(t)]
    X_moons = np.vstack([m1, m2]) + rng.normal(0, .055, (n, 2))
    y_moons = np.r_[np.zeros(n // 2, int), np.ones(n // 2, int)]

    X_small = np.array([[-4.2, .1], [-3.7, -.2], [-4.6, .7], [0, 4.1], [.6, 4.7],
                        [-.5, 3.6], [4, -1.2], [4.7, -1.8], [3.5, -.5], [7.5, 5.5]], float)
    C_small = np.array([[-4, 0], [0, 4], [4, -1]], float)
    labels_small = np.array([0, 0, 0, 1, 1, 1, 2, 2, 2, 2])
    old_C = C_small.copy(); new_C = C_small + np.array([[.01, -.01], [.02, .01], [-.01, 0]])
    # Rows are predicted clusters, columns are true classes. Row/column
    # purity differ, so the supplied example exposes an orientation error.
    contingency = np.array([[4, 1, 0], [0, 3, 1], [1, 0, 5], [2, 0, 0]], int)
    merge_distances = np.array([.18, .31, .46, .72, 1.05, 1.42, 3.85, 5.10, 6.25])

    base = np.vstack([rng.normal(-2, .55, (90, 6)), rng.normal(.7, .65, (95, 6)), rng.normal(3, .75, (85, 6))])
    mix = rng.normal(size=(6, 10)); X_high = base @ mix + rng.normal(0, .3, (270, 10))
    y_high = np.r_[np.zeros(90, int), np.ones(95, int), np.full(85, 2, int)]
    batch_idx = rng.choice(len(X_blobs), size=40, replace=False)

    # Synthetic clustering laboratory -----------------------------------------
    def shuffled(X, y):
        q = rng.permutation(len(X)); return X[q], y[q]

    # S1: compact spherical blobs
    s1 = np.vstack([rng.normal([-3, -1], .45, (55, 2)), rng.normal([0, 3], .45, (55, 2)),
                    rng.normal([3, -1], .45, (55, 2))])
    sy1 = np.repeat(np.arange(3), 55); s1, sy1 = shuffled(s1, sy1)

    # S2: anisotropic Gaussian clusters
    s2 = np.vstack([_blob(rng, [-2.8, 1.0], [[1.3, .9], [.9, .9]], 55),
                    _blob(rng, [2.6, 1.3], [[1.1, -.75], [-.75, .85]], 55),
                    _blob(rng, [0, -2.8], [[.7, .15], [.15, .28]], 55)])
    sy2 = np.repeat(np.arange(3), 55); s2, sy2 = shuffled(s2, sy2)

    # S3: unequal cluster variance/density
    s3 = np.vstack([rng.normal([-3, 0], .22, (45, 2)), rng.normal([0, 2.4], .65, (60, 2)),
                    rng.normal([3, -.5], 1.05, (60, 2))])
    sy3 = np.r_[np.zeros(45, int), np.ones(60, int), np.full(60, 2, int)]; s3, sy3 = shuffled(s3, sy3)

    # S4: two moons
    n4 = 160; tt = rng.uniform(0, np.pi, n4 // 2)
    s4 = np.vstack([np.c_[np.cos(tt), np.sin(tt)], np.c_[1 - np.cos(tt), .5 - np.sin(tt)]])
    s4 += rng.normal(0, .055, s4.shape); sy4 = np.r_[np.zeros(n4 // 2, int), np.ones(n4 // 2, int)]
    s4, sy4 = shuffled(s4, sy4)

    # S5: concentric circles
    n5 = 160; ang1 = rng.uniform(0, 2*np.pi, n5//2); ang2 = rng.uniform(0, 2*np.pi, n5//2)
    inner = np.c_[np.cos(ang1), np.sin(ang1)] + rng.normal(0, .035, (n5//2, 2))
    outer = 2.4*np.c_[np.cos(ang2), np.sin(ang2)] + rng.normal(0, .055, (n5//2, 2))
    s5 = np.vstack([inner, outer]); sy5 = np.r_[np.zeros(n5//2, int), np.ones(n5//2, int)]
    s5, sy5 = shuffled(s5, sy5)

    # S6: compact clusters plus unstructured noise. Ground-truth noise label = -1.
    core = np.vstack([rng.normal([-2.5, 0], .35, (48, 2)), rng.normal([2.5, 0], .35, (48, 2)),
                      rng.normal([0, 3], .35, (48, 2))])
    ycore = np.repeat(np.arange(3), 48)
    noise = rng.uniform([-5, -3.5], [5, 5], (20, 2))
    s6 = np.vstack([core, noise]); sy6 = np.r_[ycore, np.full(len(noise), -1, int)]
    s6, sy6 = shuffled(s6, sy6)

    # S7: synthetic high-dimensional data: 5 informative dimensions + 45 nuisance dimensions.
    n7_per = 70; informative = []
    centers = np.array([[-3, -2, 0, 1, 2], [0, 2.5, -2, 0, 1], [3, -1, 2.5, -2, 0]], float)
    for cen in centers:
        informative.append(rng.normal(cen, .65, (n7_per, 5)))
    info = np.vstack(informative)
    nuisance = rng.normal(0, 2.2, (len(info), 45))
    s7 = np.hstack([info, nuisance]); sy7 = np.repeat(np.arange(3), n7_per)
    s7 = _standardize(s7); s7, sy7 = shuffled(s7, sy7)

    # Scalability datasets ------------------------------------------------------
    scale_centers=np.array([[-6,-2],[-3,4],[0,0],[3.5,4],[6,-2]],float)
    def make_scale_dataset(total_n):
        counts=np.full(5,total_n//5,int); counts[:total_n%5]+=1; parts=[]; labels=[]
        for k,(cen,nk) in enumerate(zip(scale_centers,counts)):
            parts.append(rng.normal(cen,.75,(int(nk),2))); labels.append(np.full(int(nk),k,int))
        Xs=np.vstack(parts); ys=np.concatenate(labels); q=rng.permutation(len(Xs)); return Xs[q],ys[q]
    scale_500_X,scale_500_y=make_scale_dataset(500)
    scale_2000_X,scale_2000_y=make_scale_dataset(2000)
    scale_6000_X,scale_6000_y=make_scale_dataset(6000)

    # Real datasets -------------------------------------------------------------
    iris_raw, iris_scaled, iris_y = _load_iris()
    wine_raw, wine_scaled, wine_y = _load_wine()
    peng_raw, peng_scaled, peng_y = _load_penguins()
    wholesale_raw, wholesale_scaled, wholesale_y = _load_wholesale()
    digits_raw, digits_scaled, digits_y = _load_digits(max_per_class=70)

    # Keep the general laboratory datasets modest for from-scratch hierarchical methods.
    peng_lab_X, peng_lab_y = _balanced_subsample(rng, peng_scaled, peng_y, 180)
    wholesale_lab_X, wholesale_lab_y = _balanced_subsample(rng, wholesale_scaled, wholesale_y, 180)

    np.savez(
        file_path,
        X_blobs=X_blobs, y_blobs=y_blobs, X_aniso=X_aniso, y_aniso=y_aniso,
        X_moons=X_moons, y_moons=y_moons, X_small=X_small, C_small=C_small,
        labels_small=labels_small, old_C=old_C, new_C=new_C, contingency=contingency,
        merge_distances=merge_distances, X_high=X_high, y_high=y_high, batch_idx=batch_idx,
        # Task 16 now includes core, border, and noise points on X_small.
        eps=np.array(1.0), min_pts=np.array(3), K=np.array(3), max_K=np.array(6),
        query=np.array([1.0, 2.0]), reference=np.array([4.0, -2.0]),
        # synthetic lab
        synth_blobs_X=s1, synth_blobs_y=sy1,
        synth_aniso_X=s2, synth_aniso_y=sy2,
        synth_unequal_X=s3, synth_unequal_y=sy3,
        synth_moons_X=s4, synth_moons_y=sy4,
        synth_circles_X=s5, synth_circles_y=sy5,
        synth_noise_X=s6, synth_noise_y=sy6,
        synth_highdim_X=s7, synth_highdim_y=sy7,
        # real lab
        iris_raw_X=iris_raw, iris_X=iris_scaled, iris_y=iris_y,
        wine_raw_X=wine_raw, wine_X=wine_scaled, wine_y=wine_y,
        penguins_raw_X=peng_raw, penguins_X=peng_lab_X, penguins_y=peng_lab_y,
        wholesale_raw_X=wholesale_raw, wholesale_X=wholesale_lab_X, wholesale_y=wholesale_lab_y,
        digits_raw_X=digits_raw, digits_X=digits_scaled, digits_y=digits_y,
        scale_500_X=scale_500_X, scale_500_y=scale_500_y,
        scale_2000_X=scale_2000_X, scale_2000_y=scale_2000_y,
        scale_6000_X=scale_6000_X, scale_6000_y=scale_6000_y,
    )
    _write_visualization_helper()
    print(f"Created {file_path}")
    print("Created visualization.py")
    print("Atomic datasets:", X_blobs.shape, X_aniso.shape, X_moons.shape, X_high.shape)
    print("Synthetic laboratory:", s1.shape, s2.shape, s3.shape, s4.shape, s5.shape, s6.shape, s7.shape)
    print("Real laboratory:", iris_scaled.shape, wine_scaled.shape, peng_lab_X.shape, wholesale_lab_X.shape, digits_scaled.shape)
    print("Scalability laboratory:", scale_500_X.shape, scale_2000_X.shape, scale_6000_X.shape)


if __name__ == "__main__":
    generate_data()
