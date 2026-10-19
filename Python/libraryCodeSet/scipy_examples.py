"""SciPy — practical single-file examples.

Install:  pip install scipy numpy
Run:      python scipy_examples.py

Covers constants, integration, optimization, interpolation, linear algebra,
statistics, signal processing, sparse matrices, spatial algorithms, and
n-dimensional image filtering.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

import numpy as np
import scipy
from scipy import constants, fft, integrate, interpolate, linalg, ndimage, optimize
from scipy import signal, sparse, spatial, stats
from scipy.cluster import hierarchy
from scipy.sparse.linalg import spsolve


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Constants
# ---------------------------------------------------------------------------
def physical_constants() -> None:
    section("1. Physical constants")

    print("scipy version:", scipy.__version__)
    print("speed of light:", constants.c, "m/s")
    print("Planck:", constants.h, "J·s")
    print("elementary charge:", constants.e, "C")
    print("Avogadro:", constants.N_A, "1/mol")

    # Units: convert kilometres to miles, energy to electronvolts
    print("10 km in miles:", constants.kilo / constants.mile * 10)
    print("1 eV in joules:", constants.electron_volt)
    print("0 °C in kelvin:", constants.convert_temperature(0, "C", "K"))

    # CODATA dictionary lookup
    entry = constants.physical_constants["proton mass"]
    print("proton mass:", entry[0], entry[1], entry[2])


# ---------------------------------------------------------------------------
# 2. Numerical integration
# ---------------------------------------------------------------------------
def integration() -> None:
    section("2. Integration and ODEs")

    # Single integral: ∫ sin(x) dx from 0 to π = 2
    value, error = integrate.quad(np.sin, 0, np.pi)
    print("quad(sin, 0, pi):", value, "error:", error)

    # Integrand with parameters
    def gaussian(x: float, mu: float, sigma: float) -> float:
        return np.exp(-0.5 * ((x - mu) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))

    area, _ = integrate.quad(gaussian, -np.inf, np.inf, args=(0.0, 1.0))
    print("normal pdf area:", area)

    # Double integral over a unit square
    double, _ = integrate.dblquad(lambda y, x: x * y, 0, 1, 0, 1)
    print("∫∫ x*y over [0,1]²:", double)

    # Discrete cumulative trapezoid
    x = np.linspace(0, np.pi, 1001)
    print("trapezoid sin:", integrate.trapezoid(np.sin(x), x))
    print("cumulative trapezoid (last):", integrate.cumulative_trapezoid(np.sin(x), x)[-1])

    # Initial value problem: y' = -2y, y(0) = 1  →  y = exp(-2t)
    def decay(t: float, y: np.ndarray) -> np.ndarray:
        return -2.0 * y

    solution = integrate.solve_ivp(decay, (0, 3), [1.0], t_eval=np.linspace(0, 3, 7), rtol=1e-9)
    print("solve_ivp t:", solution.t)
    print("solve_ivp y:", solution.y[0])

    # Damped oscillator as a first-order system
    def oscillator(t: float, state: np.ndarray) -> list[float]:
        position, velocity = state
        return [velocity, -0.4 * velocity - 4.0 * position]

    osc = integrate.solve_ivp(oscillator, (0, 10), [1.0, 0.0], t_eval=np.linspace(0, 10, 5))
    print("oscillator positions:", osc.y[0])


# ---------------------------------------------------------------------------
# 3. Optimization and root finding
# ---------------------------------------------------------------------------
def optimization() -> None:
    section("3. Optimization and root finding")

    # Minimize a quadratic bowl
    def bowl(xy: np.ndarray) -> float:
        x, y = xy
        return (x - 2) ** 2 + (y + 1) ** 2 + 3

    result = optimize.minimize(bowl, x0=[0.0, 0.0], method="Nelder-Mead")
    print("minimum:", result.x, "value:", result.fun, "success:", result.success)

    # Constrained minimization with bounds
    result = optimize.minimize(
        lambda x: (x[0] - 3) ** 2 + (x[1] - 1) ** 2,
        x0=[0.0, 0.0],
        bounds=[(0, 1), (0, 1)],
        method="L-BFGS-B",
    )
    print("bounded minimum:", result.x)

    # Root finding: x³ - 2x - 5 = 0
    root = optimize.root_scalar(lambda x: x**3 - 2 * x - 5, bracket=[1, 3], method="brentq")
    print("root:", root.root, "iterations:", root.iterations)

    # Curve fitting: y = a * exp(-b t) + c
    rng = np.random.default_rng(5)
    t = np.linspace(0, 5, 25)
    truth = (3.0, 0.8, 0.5)
    observed = truth[0] * np.exp(-truth[1] * t) + truth[2] + rng.normal(scale=0.05, size=t.size)

    def model(time: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
        return a * np.exp(-b * time) + c

    popt, pcov = optimize.curve_fit(model, t, observed, p0=[1.0, 1.0, 0.0])
    print("curve_fit params:", np.round(popt, 3))
    print("param stderr:", np.round(np.sqrt(np.diag(pcov)), 4))

    # Linear programming: maximize 3x + 2y subject to x + y <= 4, x <= 2, y <= 3
    # linprog minimizes, so negate the objective.
    lp = optimize.linprog(
        c=[-3, -2],
        A_ub=[[1, 1]],
        b_ub=[4],
        bounds=[(0, 2), (0, 3)],
        method="highs",
    )
    print("linprog objective:", -lp.fun, "x:", lp.x)


# ---------------------------------------------------------------------------
# 4. Interpolation
# ---------------------------------------------------------------------------
def interpolation() -> None:
    section("4. Interpolation and smoothing")

    x = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0])
    y = np.sin(x)

    linear = interpolate.interp1d(x, y, kind="linear")
    cubic = interpolate.interp1d(x, y, kind="cubic")
    query = np.linspace(0, 5, 9)
    print("linear:", np.round(linear(query), 4))
    print("cubic: ", np.round(cubic(query), 4))

    # CubicSpline offers derivatives and antiderivatives
    spline = interpolate.CubicSpline(x, y)
    print("spline derivative at 2:", spline(2.0, 1))
    print("spline integral 0..5:", spline.antiderivative()(5.0) - spline.antiderivative()(0.0))

    # Smoothing spline on noisy data
    rng = np.random.default_rng(9)
    noisy_x = np.linspace(0, 10, 80)
    noisy_y = np.sin(noisy_x) + rng.normal(scale=0.2, size=noisy_x.size)
    smoothing = interpolate.UnivariateSpline(noisy_x, noisy_y, s=1.5)
    print("smoothing residuals:", round(float(np.sum((smoothing(noisy_x) - noisy_y) ** 2)), 4))

    # Regular grid interpolation (2-D)
    grid_x, grid_y = np.mgrid[0:5:6j, 0:5:6j]
    grid_z = np.sin(grid_x) * np.cos(grid_y)
    points = np.column_stack([grid_x.ravel(), grid_y.ravel()])
    values = grid_z.ravel()
    fine_x, fine_y = np.mgrid[0:5:20j, 0:5:20j]
    fine_z = interpolate.griddata(points, values, (fine_x, fine_y), method="cubic")
    print("griddata shape:", fine_z.shape, "finite values:", np.isfinite(fine_z).sum())


# ---------------------------------------------------------------------------
# 5. Linear algebra
# ---------------------------------------------------------------------------
def linear_algebra() -> None:
    section("5. Linear algebra")

    a = np.array([[4.0, 1.0, 0.0], [1.0, 3.0, 1.0], [0.0, 1.0, 2.0]])
    b = np.array([1.0, 2.0, 3.0])

    lu, piv = linalg.lu_factor(a)
    solution = linalg.lu_solve((lu, piv), b)
    print("LU solve:", solution, "residual:", np.linalg.norm(a @ solution - b))

    # Cholesky for symmetric positive-definite matrices
    chol = linalg.cholesky(a, lower=True)
    print("Cholesky lower:\n", chol)
    print("reconstruction ok:", np.allclose(chol @ chol.T, a))

    # Eigenvalues and SVD
    eigenvalues, eigenvectors = linalg.eigh(a)
    print("eigenvalues:", eigenvalues)
    u, s, vh = linalg.svd(a)
    print("singular values:", s)
    print("condition number:", np.linalg.cond(a))

    # Sparse matrices: build a tridiagonal system
    n = 10
    main = 2.0 * np.ones(n)
    off = -1.0 * np.ones(n - 1)
    sparse_matrix = sparse.diags([off, main, off], offsets=[-1, 0, 1], format="csr")
    rhs = np.ones(n)
    sparse_solution = spsolve(sparse_matrix, rhs)
    print("\nsparse solve shape:", sparse_solution.shape)
    print("sparse nnz:", sparse_matrix.nnz)
    print("sparse solution mean:", round(float(sparse_solution.mean()), 4))


# ---------------------------------------------------------------------------
# 6. Statistics
# ---------------------------------------------------------------------------
def statistics() -> None:
    section("6. Probability distributions and statistical tests")

    normal = stats.norm(loc=100, scale=15)
    print("pdf(100):", round(normal.pdf(100), 6))
    print("cdf(120):", round(normal.cdf(120), 6))
    print("ppf(0.95):", round(normal.ppf(0.95), 4))
    print("random sample (seeded):", np.round(normal.rvs(size=5, random_state=42), 2))

    # Other distributions
    print("\nbinomial mean:", stats.binom.mean(n=20, p=0.3))
    print("poisson pmf(3):", round(stats.poisson.pmf(3, mu=4), 6))
    print("t critical value:", round(stats.t.ppf(0.975, df=10), 4))

    rng = np.random.default_rng(12)
    group_a = rng.normal(loc=50, scale=8, size=60)
    group_b = rng.normal(loc=54, scale=8, size=60)

    t_stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
    print("\nWelch t-test: t =", round(float(t_stat), 3), "p =", round(float(p_value), 4))

    u_stat, u_p = stats.mannwhitneyu(group_a, group_b)
    print("Mann-Whitney U: U =", round(float(u_stat), 1), "p =", round(float(u_p), 4))

    r, r_p = stats.pearsonr(group_a, group_b)
    print("Pearson r:", round(float(r), 3), "p:", round(float(r_p), 4))

    slope, intercept, r_value, p_value, std_err = stats.linregress(group_a, group_b)
    print("linregress slope/intercept:", round(slope, 3), round(intercept, 3))

    # Normality test
    stat, p = stats.shapiro(group_a)
    print("Shapiro-Wilk p:", round(float(p), 4))

    # Summary statistics
    print("\ndescribe:", np.round(stats.describe(group_a), 3))


# ---------------------------------------------------------------------------
# 7. Signal processing
# ---------------------------------------------------------------------------
def signal_processing() -> None:
    section("7. Signal processing")

    sample_rate = 500.0
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    clean = np.sin(2 * np.pi * 5 * t) + 0.4 * np.sin(2 * np.pi * 40 * t)
    rng = np.random.default_rng(4)
    noisy = clean + rng.normal(scale=0.35, size=clean.size)

    # Butterworth low-pass filter, applied forward and backward (zero phase)
    b, a = signal.butter(N=4, Wn=15, btype="low", fs=sample_rate)
    filtered = signal.filtfilt(b, a, noisy)
    print("noisy std:", round(float(noisy.std()), 3), "filtered std:", round(float(filtered.std()), 3))
    print("filter coefficients b:", np.round(b, 4))

    # Frequency response
    frequencies, response = signal.freqz(b, a, fs=sample_rate)
    print("gain at 5 Hz:", round(float(np.abs(response[np.argmin(np.abs(frequencies - 5))])), 4))

    # Peak detection
    peaks, properties = signal.find_peaks(filtered, height=0.3, distance=50)
    print("peaks found:", peaks.size, "first heights:", np.round(properties["peak_heights"][:4], 3))

    # Spectrogram
    freqs, times, sxx = signal.spectrogram(noisy, fs=sample_rate, nperseg=128, noverlap=96)
    print("spectrogram shape:", sxx.shape)
    dominant = freqs[np.argmax(sxx.mean(axis=1))]
    print("dominant frequency:", round(float(dominant), 2), "Hz")

    # Convolution and correlation
    kernel = np.ones(9) / 9
    print("moving average first 5:", np.round(signal.convolve(noisy, kernel, mode="same")[:5], 3))
    print("autocorrelation peak lag:", int(np.argmax(signal.correlate(clean, clean, mode="full")) - clean.size + 1))

    # Resampling
    resampled = signal.resample(clean, clean.size // 2)
    print("resampled length:", resampled.size)


# ---------------------------------------------------------------------------
# 8. Spatial algorithms
# ---------------------------------------------------------------------------
def spatial_algorithms() -> None:
    section("8. Spatial distance and nearest neighbours")

    points = np.array(
        [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [3.0, 3.0],
            [3.1, 2.9],
        ]
    )

    print("Euclidean distances from point 0:", np.round(spatial.distance.cdist(points[:1], points)[0], 3))
    print("cityblock:", np.round(spatial.distance.cityblock(points[0], points[3]), 3))
    print("cosine:", np.round(spatial.distance.cosine(points[0], points[1]), 3))

    tree = spatial.KDTree(points)
    distances, indices = tree.query([[0.2, 0.1], [2.9, 3.0]], k=2)
    print("kNN distances:", np.round(distances, 3))
    print("kNN indices:", indices)

    # Pairwise distance matrix and linkage for hierarchical clustering
    matrix = spatial.distance.pdist(points)
    linkage = hierarchy.linkage(matrix, method="average")
    print("condensed distance matrix:", np.round(matrix, 3))
    print("linkage shape:", linkage.shape)
    print("cluster labels:", hierarchy.fcluster(linkage, t=2.0, criterion="distance"))


# ---------------------------------------------------------------------------
# 9. N-dimensional image filtering
# ---------------------------------------------------------------------------
def image_filtering() -> None:
    section("9. ndimage filtering and morphology")

    rng = np.random.default_rng(8)
    image = rng.random((40, 60))
    # Add a bright square and a dark disk
    image[8:18, 10:25] += 0.8
    image[25:35, 35:55] -= 0.6
    image = np.clip(image, 0, 1)

    smoothed = ndimage.gaussian_filter(image, sigma=1.5)
    print("original range:", round(float(image.min()), 3), round(float(image.max()), 3))
    print("smoothed range:", round(float(smoothed.min()), 3), round(float(smoothed.max()), 3))

    edges = ndimage.sobel(smoothed, axis=0) ** 2 + ndimage.sobel(smoothed, axis=1) ** 2
    print("edge energy:", round(float(edges.sum()), 2))

    # Threshold and label connected components
    mask = smoothed > 0.55
    labels, count = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    print("components:", count, "sizes:", sizes.astype(int))

    # Morphology
    eroded = ndimage.binary_erosion(mask, iterations=1)
    dilated = ndimage.binary_dilation(mask, iterations=1)
    print("mask / eroded / dilated pixels:", mask.sum(), eroded.sum(), dilated.sum())

    # Rotate and zoom
    rotated = ndimage.rotate(image, angle=15, reshape=False, order=1)
    zoomed = ndimage.zoom(image, zoom=0.5, order=1)
    print("rotated shape:", rotated.shape, "zoomed shape:", zoomed.shape)


# ---------------------------------------------------------------------------
# 10. FFT helpers
# ---------------------------------------------------------------------------
def fft_helpers() -> None:
    section("10. FFT helpers")

    rng = np.random.default_rng(1)
    x = rng.normal(size=256)
    spectrum = fft.fft(x)
    print("fft length:", spectrum.size, "dtype:", spectrum.dtype)
    print("Parseval check:", np.allclose(np.sum(np.abs(x) ** 2), np.sum(np.abs(spectrum) ** 2) / x.size))

    frequencies = fft.fftfreq(x.size, d=1 / 256)
    power = np.abs(spectrum) ** 2
    top = np.argsort(power)[-3:]
    print("top power frequencies:", np.round(frequencies[top], 2))

    # Linear convolution through FFT (pad to avoid circular wrap-around)
    kernel = np.array([1.0, 2.0, 1.0])
    size = x[:32].size + kernel.size - 1
    direct = np.convolve(x[:32], kernel, mode="full")
    via_fft = fft.irfft(fft.rfft(x[:32], n=size) * fft.rfft(kernel, n=size), n=size)
    print("fft convolution close:", np.allclose(direct, via_fft, atol=1e-8))

    # DCT is useful for compression-style features
    cosine = fft.dct(x[:64], type=2, norm="ortho")
    print("DCT first coefficients:", np.round(cosine[:5], 3))


def main() -> None:
    physical_constants()
    integration()
    optimization()
    interpolation()
    linear_algebra()
    statistics()
    signal_processing()
    spatial_algorithms()
    image_filtering()
    fft_helpers()

    print("\nAll SciPy example sections completed.")


if __name__ == "__main__":
    main()
