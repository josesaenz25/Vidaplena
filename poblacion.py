"""Referencia demográfica de la CDMX por alcaldía (fuente de verdad única para toda la app).

- pob60_est: población de 60+ años ESTIMADA (aproximada), cifras de referencia del proyecto
  basadas en el Censo de Población y Vivienda 2020 (INEGI) y estadísticas de envejecimiento del Gobierno de la CDMX.
- pob_total_2020: población total, Censo 2020 (INEGI, Panorama sociodemográfico de Ciudad de México 2020).
- pct65_2020: % de población de 65+ años por alcaldía (INEGI, Panorama sociodemográfico CDMX 2020).
"""
import pandas as pd

FUENTE = ("Censo de Población y Vivienda 2020 (INEGI) y estadísticas de envejecimiento del Gobierno de la CDMX. "
          "La población de 60+ por alcaldía es una estimación aproximada.")

# nombre en la base: (pob60_est, pob_total_2020, pct65_2020)
REF = {
    "Iztapalapa": (280_000, 1_835_486, 9.5),
    "Gustavo A. Madero": (220_000, 1_173_351, 12.0),
    "Coyoacán": (165_000, 614_447, 14.7),
    "Álvaro Obregón": (145_000, 759_137, 11.0),
    "Tlalpan": (135_000, 699_928, 10.6),
    "Cuauhtémoc": (105_000, 545_884, 11.8),
    "Azcapotzalco": (100_000, 432_205, 12.7),
    "Venustiano Carranza": (92_000, 443_704, 12.2),
    "Miguel Hidalgo": (88_000, 414_470, 12.1),
    "Iztacalco": (82_000, 404_695, 12.1),
    "Xochimilco": (78_000, 442_178, 9.2),
    "Benito Juárez": (70_000, 434_153, 14.2),
    "Tláhuac": (65_000, 392_313, 7.5),
    "La Magdalena Contreras": (42_000, 247_622, 10.5),
    "Cuajimalpa": (34_000, 217_686, 7.7),
    "Milpa Alta": (20_000, 152_685, 7.0),
}
TOTAL_60 = sum(v[0] for v in REF.values())          # ≈ 1.7 millones
TOP_NUMERO = ["Iztapalapa", "Gustavo A. Madero", "Coyoacán", "Álvaro Obregón", "Tlalpan"]
TOP_PROPORCION = ["Benito Juárez", "Coyoacán", "Miguel Hidalgo", "Azcapotzalco", "Cuauhtémoc"]


def referencia() -> pd.DataFrame:
    df = pd.DataFrame([(k, *v) for k, v in REF.items()],
                      columns=["alcaldia", "pob60_est", "pob_total_2020", "pct65_2020"])
    df["rank_numero"] = df.pob60_est.rank(ascending=False, method="min").astype(int)
    df["rank_proporcion"] = df.pct65_2020.rank(ascending=False, method="min").astype(int)
    return df


def con_cobertura(adultos_por_alcaldia: pd.Series) -> pd.DataFrame:
    """Une la referencia con los adultos registrados en el programa por alcaldía."""
    df = referencia().set_index("alcaldia")
    df["registrados"] = adultos_por_alcaldia.reindex(df.index).fillna(0).astype(int)
    df["por_10mil"] = (df.registrados / df.pob60_est * 10_000).round(1)
    return df.reset_index()
