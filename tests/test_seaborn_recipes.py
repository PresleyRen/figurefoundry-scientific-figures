"""Real custom-backend export and semantic-data preservation checks."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "examples"))
sys.path.insert(0, str(ROOT / "skills" / "figurefoundry" / "scripts"))


@unittest.skipUnless(importlib.util.find_spec("seaborn"), "Optional Seaborn recipe dependency is absent")
class SeabornRecipeTests(unittest.TestCase):
    def test_weighted_mean_uses_declared_weights_and_preserves_zero_weight_rows(self):
        from ff_seaborn import weighted_summary
        result = weighted_summary([1, 10, 100], [1, 2, 0], weight_definition="declared exposure weights")
        self.assertAlmostEqual(result["mean"], 7)
        self.assertEqual(result["rows"], 3)
        self.assertEqual(result["positive_weight_rows"], 2)
        self.assertIsNone(result["uncertainty"])
        for weights in ([0, 0], [1, -1], [1, float("inf")]):
            with self.subTest(weights=weights):
                with self.assertRaises(ValueError):
                    weighted_summary([1, 2], weights, weight_definition="exposure")

    def test_four_grid_recipes_keep_live_labels_native_shapes_and_source(self):
        from custom_seaborn import KINDS, export_recipe, synthetic_data
        frame = synthetic_data()
        original = frame.copy(deep=True)
        with tempfile.TemporaryDirectory() as directory:
            for kind in KINDS:
                with self.subTest(kind=kind):
                    report = export_recipe(kind, frame, Path(directory) / kind, formats=("svg",), data_status="synthetic")
                    self.assertTrue(report["svg_audit"]["passed"])
                    self.assertEqual(report["svg_audit"]["metrics"]["image_count"], 0)
                    self.assertGreater(report["svg_audit"]["metrics"]["text_count"], 6)
                    self.assertIn("Synthetic demonstration", (Path(directory) / f"{kind}.svg").read_text())
                    self.assertTrue(frame.equals(original))

    def test_recipe_requires_explicit_missing_value_decision(self):
        from custom_seaborn import build_recipe, synthetic_data
        import numpy as np
        frame = synthetic_data()
        frame.loc[0, "response"] = np.nan
        with self.assertRaisesRegex(ValueError, "missing"):
            build_recipe("facet", frame)

    def test_cluster_records_actual_members_and_normalization(self):
        from custom_seaborn import build_recipe, synthetic_data
        import matplotlib.pyplot as plt
        frame = synthetic_data()
        fig, _, _, metadata = build_recipe("cluster", frame)
        try:
            self.assertEqual(set(metadata["row_order"]), set(frame["unit"]))
            self.assertIn("z-score", metadata["transform"])
            self.assertEqual(metadata["linkage"], "average")
        finally:
            plt.close(fig)

    def test_cluster_header_separates_colorbar_and_trees_without_losing_rows(self):
        from ff_seaborn import build_recipe, synthetic_data
        import matplotlib.pyplot as plt
        import numpy as np
        frame = synthetic_data()
        fig, width, height, metadata = build_recipe("cluster", frame, data_status="synthetic")
        try:
            fig.set_size_inches(width / 25.4, height / 25.4)
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            axes = {ax.get_gid(): ax for ax in fig.axes}
            colorbar_box = axes["ff-cluster-colorbar"].get_tightbbox(renderer)
            for role in ("heatmap", "row-dendrogram", "column-dendrogram"):
                with self.subTest(role=role):
                    self.assertFalse(colorbar_box.overlaps(
                        axes[f"ff-cluster-{role}"].get_window_extent(renderer)))
            title_box = fig._suptitle.get_window_extent(renderer)
            tree_box = axes["ff-cluster-column-dendrogram"].get_window_extent(renderer)
            self.assertGreater(title_box.y0 - tree_box.y1, 2 * fig.dpi / 25.4)

            heatmap = axes["ff-cluster-heatmap"]
            labels = [label.get_text() for label in heatmap.get_yticklabels()]
            self.assertEqual(len(labels), 48)
            self.assertEqual(labels, metadata["row_order"])
            self.assertEqual(set(labels), set(frame["unit"]))
            columns = [label.get_text() for label in heatmap.get_xticklabels()]
            matrix = frame.set_index("unit")[["dose", "response", "signal"]]
            zscores = (matrix - matrix.mean()) / matrix.std(ddof=1)
            mesh = heatmap.collections[0]
            np.testing.assert_allclose(np.asarray(mesh.get_array()).reshape(48, 3),
                                       zscores.loc[labels, columns].to_numpy())
            self.assertEqual((mesh.norm.vmin, mesh.norm.vmax), (-2, 2))
            self.assertEqual(metadata["linkage"], "average")
            self.assertEqual(metadata["distance"], "euclidean")
        finally:
            plt.close(fig)

    def test_pair_density_uses_panel_height_without_changing_bins_or_observations(self):
        from ff_seaborn import PALETTE, build_recipe, synthetic_data
        import matplotlib.pyplot as plt
        import numpy as np
        frame = synthetic_data()
        fig, width, height, metadata = build_recipe("pair", frame)
        try:
            fig.set_size_inches(width / 25.4, height / 25.4)
            fig.canvas.draw()
            for variable in ("dose", "response", "signal"):
                ax = next(ax for ax in fig.axes if ax.get_gid() == f"ff-pair-density-{variable}")
                edges = np.asarray(metadata["histogram_bins"][variable])
                self.assertEqual(len(ax.patches), len(PALETTE))
                for patch in ax.patches:
                    values = frame.loc[frame["method"] == patch.get_label(), variable]
                    counts, _ = np.histogram(values, bins=edges)
                    # Hand-defined density: bin count / (method n * bin width).
                    density = counts / (len(values) * np.diff(edges))
                    vertices = patch.get_xy()
                    np.testing.assert_allclose(vertices[1:-1:2, 0], edges[:-1])
                    np.testing.assert_allclose(vertices[1:-1:2, 1], density)
                    self.assertAlmostEqual(float(np.sum(density * np.diff(edges))), 1)
                peak = max(float(patch.get_xy()[:, 1].max()) for patch in ax.patches)
                self.assertGreater(peak / ax.get_ylim()[1], 0.9)

            scatter_axes = [ax for ax in fig.axes if ax.collections]
            self.assertEqual(len(scatter_axes), 3)
            for ax, columns in zip(scatter_axes,
                                   (("dose", "response"), ("dose", "signal"), ("response", "signal"))):
                observed = np.vstack([collection.get_offsets() for collection in ax.collections])
                self.assertEqual(len(observed), 48)
                np.testing.assert_allclose(sorted(map(tuple, observed)),
                                           sorted(map(tuple, frame[list(columns)].to_numpy())))
        finally:
            plt.close(fig)


if __name__ == "__main__":
    unittest.main()
