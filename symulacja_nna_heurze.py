"""Demonstracyjna sieć informacji i perkolacja fałszywej wiadomości.

Wymagania: networkx, numpy, matplotlib
Instalacja: python -m pip install networkx numpy matplotlib
Uruchomienie: python networkx_defence_demo.py

Wszystkie konta, wiadomości, wagi i wyniki są syntetyczne. Model jest
heurystyką demonstracyjną, a nie wytrenowanym ani zwalidowanym predyktorem.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch
from matplotlib.animation import FuncAnimation, PillowWriter
import networkx as nx
import numpy as np

SEED = 17
RNG = np.random.default_rng(SEED)
TOPICS = ["moda", "polityka", "życie społeczne", "zdrowie", "technologia"]


def make_person(
    node_id: str,
    name: str,
    role: str,
    attachment: list[float],
    *,
    handle: str,
    verified: bool = False,
    credibility: float = 0.5,
    account_age_days: int = 500,
    impersonates: str | None = None,
) -> dict[str, Any]:
    """Zwraca atrybuty syntetycznego konta; attachment odpowiada kolejności TOPICS."""
    return {
        "name": name,
        "role": role,
        "attachment": np.array(attachment, dtype=float),
        "handle": handle,
        "verified": verified,
        "credibility": float(credibility),
        "account_age_days": account_age_days,
        "impersonates": impersonates,
    }


# Pięć autentycznych kont influencerów.
people: dict[str, dict[str, Any]] = {
    "I1": make_person("I1", "Lena Style", "influencer", [0.95, 0.25, 0.55, 0.35, 0.40], handle="@lena_style", verified=True, credibility=0.92, account_age_days=1800),
    "I2": make_person("I2", "Marek Obywatel", "influencer", [0.20, 0.94, 0.75, 0.30, 0.35], handle="@marek_obywatel", verified=True, credibility=0.89, account_age_days=1600),
    "I3": make_person("I3", "Ola Razem", "influencer", [0.35, 0.60, 0.96, 0.45, 0.25], handle="@ola_razem", verified=True, credibility=0.90, account_age_days=1500),
    "I4": make_person("I4", "Doktor Rytm", "influencer", [0.20, 0.25, 0.50, 0.96, 0.30], handle="@doktor_rytm", verified=True, credibility=0.93, account_age_days=2200),
    "I5": make_person("I5", "Ada Tech", "influencer", [0.30, 0.35, 0.45, 0.25, 0.97], handle="@ada_tech", verified=True, credibility=0.91, account_age_days=1300),
    # Fałszywe konto ma podobny uchwyt i profil do I1, ale jest nowe i niezweryfikowane.
    "F1": make_person("F1", "Lena Style Official", "fake", [0.91, 0.28, 0.51, 0.37, 0.43], handle="@lena_style_official", verified=False, credibility=0.68, account_age_days=9, impersonates="I1"),
}

# Dziesięciu odbiorców. Wagi są celowo syntetyczne i mieszczą się w [0, 1].
recipient_profiles = [
    [0.82, 0.20, 0.52, 0.30, 0.35], [0.25, 0.88, 0.68, 0.28, 0.40],
    [0.40, 0.55, 0.91, 0.46, 0.30], [0.18, 0.22, 0.42, 0.90, 0.36],
    [0.32, 0.31, 0.45, 0.25, 0.91], [0.76, 0.62, 0.58, 0.40, 0.52],
    [0.28, 0.78, 0.82, 0.37, 0.33], [0.62, 0.35, 0.48, 0.83, 0.42],
    [0.46, 0.40, 0.62, 0.54, 0.79], [0.55, 0.73, 0.70, 0.48, 0.66],
]
for i, profile in enumerate(recipient_profiles, start=1):
    rid = f"R{i:02d}"
    people[rid] = make_person(
        rid, f"Odbiorca {i:02d}", "recipient", profile,
        handle=f"@odbiorca_{i:02d}", credibility=0.55,
        account_age_days=300 + 37 * i,
    )

# Graf wielokrawędziowy zachowuje osobne wiadomości, także gdy nadawca i odbiorca
# wymieniają więcej niż jedną wiadomość.
G = nx.MultiDiGraph()
for node_id, attrs in people.items():
    G.add_node(node_id, **attrs)

message_counter = 0

def add_message(source: str, target: str, topic: str, text: str, *, false: bool = False,
                virality: float = 0.5, salience: float = 0.5) -> None:
    global message_counter
    message_counter += 1
    G.add_edge(
        source, target, key=f"M{message_counter:02d}",
        message_id=f"M{message_counter:02d}", topic=topic, text=text,
        is_false=false, virality=float(virality), salience=float(salience),
    )

# Kontakty między influencerami oraz ich zwykłe wiadomości.
for source, target, topic in [
    ("I1", "I2", "życie społeczne"), ("I2", "I3", "polityka"),
    ("I3", "I4", "życie społeczne"), ("I4", "I5", "zdrowie"),
    ("I5", "I1", "technologia"), ("I2", "I5", "technologia"),
]:
    add_message(source, target, topic, f"Rozmowa o temacie: {topic}.", virality=0.35)

# Wiadomości influencerów do odbiorców.
for influencer, recipients, topic in [
    ("I1", ["R01", "R06", "R08", "R10"], "moda"),
    ("I2", ["R02", "R06", "R07", "R10"], "polityka"),
    ("I3", ["R03", "R06", "R07", "R09"], "życie społeczne"),
    ("I4", ["R04", "R08", "R09"], "zdrowie"),
    ("I5", ["R05", "R09", "R10"], "technologia"),
]:
    for recipient in recipients:
        add_message(influencer, recipient, topic, f"Wiadomość informacyjna o: {topic}.", virality=0.45, salience=0.35)

# Fałszywa wiadomość podszywającego się konta oraz kilka prawdziwych wiadomości.
add_message("F1", "R01", "moda", "Fałszywa promocja rzekomo od Leny Style.", false=True, virality=0.88, salience=0.82)
add_message("F1", "R02", "moda", "Ta sama fałszywa promocja wysłana dalej.", false=True, virality=0.88, salience=0.82)
add_message("F1", "R06", "moda", "Pilna, niepotwierdzona wiadomość od podszywającego się konta.", false=True, virality=0.92, salience=0.90)
add_message("F1", "I1", "moda", "Fałszywe konto próbuje nawiązać kontakt z osobą, pod którą się podszywa.", false=True, virality=0.55, salience=0.45)
add_message("I1", "R01", "moda", "Prawdziwa informacja o nowej kolekcji.", virality=0.50, salience=0.40)

# Część odbiorców wchodzi w interakcje z innymi odbiorcami.
for source, target, topic in [
    ("R01", "R03", "życie społeczne"), ("R02", "R07", "polityka"),
    ("R03", "R06", "życie społeczne"), ("R04", "R08", "zdrowie"),
    ("R05", "R09", "technologia"), ("R06", "R10", "moda"),
    ("R07", "R03", "polityka"), ("R08", "R01", "zdrowie"),
    ("R09", "R10", "technologia"), ("R10", "R02", "życie społeczne"),
]:
    add_message(source, target, topic, f"Rozmowa odbiorców o: {topic}.", virality=0.30, salience=0.25)


def topic_index(topic: str) -> int:
    return TOPICS.index(topic)


def normalized_handle(handle: str) -> str:
    return re.sub(r"[^a-z0-9]", "", handle.lower().lstrip("@"))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def impersonation_scan(graph: nx.MultiDiGraph, threshold: float = 0.70) -> list[dict[str, Any]]:
    """Heurystyka: podobna nazwa, podobny profil, brak weryfikacji i młode konto."""
    findings = []
    real_accounts = [n for n, d in graph.nodes(data=True) if d["role"] == "influencer"]
    candidates = [n for n, d in graph.nodes(data=True) if d["role"] != "influencer"]
    for candidate in candidates:
        c = graph.nodes[candidate]
        for real in real_accounts:
            r = graph.nodes[real]
            name_sim = SequenceMatcher(None, normalized_handle(c["handle"]), normalized_handle(r["handle"])).ratio()
            profile_sim = cosine_similarity(c["attachment"], r["attachment"])
            verification_mismatch = float(r["verified"] and not c["verified"])
            new_account = float(c["account_age_days"] < 30)
            score = 0.45 * name_sim + 0.25 * profile_sim + 0.15 * verification_mismatch + 0.15 * new_account
            if score >= threshold:
                findings.append({
                    "candidate": candidate, "candidate_handle": c["handle"],
                    "lookalike_of": real, "real_handle": r["handle"],
                    "score": score, "name_similarity": name_sim,
                    "profile_similarity": profile_sim,
                })
    return sorted(findings, key=lambda x: x["score"], reverse=True)


def adoption_probability(person: dict[str, Any], source: dict[str, Any], message: dict[str, Any]) -> float:
    """Heurystyka Independent Cascade; wynik obcięty do zakresu 0.02-0.95."""
    affinity = float(person["attachment"][topic_index(message["topic"])])
    # Przy fałszywej wiadomości pozorna wiarygodność podszywającego się konta
    # nie jest automatycznie obniżana przez detektor: symulujemy brak moderacji.
    probability = (
        0.06
        + 0.44 * affinity
        + 0.22 * message["virality"]
        + 0.13 * message["salience"]
        + 0.15 * source["credibility"]
    )
    return float(np.clip(probability, 0.02, 0.95))


def run_independent_cascade(graph: nx.MultiDiGraph, seed_node: str, message: dict[str, Any], seed: int = SEED):
    """Symuluje podanie tej samej wiadomości po skierowanych kanałach kontaktu.

    Równoległe krawędzie są traktowane jako jeden kanał kontaktu, by ta sama osoba
    nie dostała kilku losowań od tego samego nadawcy w tej samej rundzie.
    """
    rng = np.random.default_rng(seed)
    active = {seed_node}
    received = {seed_node}
    attempted_pairs: set[tuple[str, str]] = set()
    attempts = []
    frontier = [seed_node]
    round_no = 0
    while frontier:
        round_no += 1
        next_frontier = []
        for source_id in frontier:
            source_attrs = graph.nodes[source_id]
            for target_id in sorted(set(graph.successors(source_id))):
                pair = (source_id, target_id)
                if target_id in active or pair in attempted_pairs:
                    continue
                attempted_pairs.add(pair)
                target_attrs = graph.nodes[target_id]
                p = adoption_probability(target_attrs, source_attrs, message)
                adopted = bool(rng.random() < p)
                attempts.append({"round": round_no, "source": source_id, "target": target_id, "p": p, "adopted": adopted})
                received.add(target_id)
                if adopted:
                    active.add(target_id)
                    next_frontier.append(target_id)
        frontier = next_frontier
    return active, received, attempts


def draw_graph(graph: nx.MultiDiGraph, filename: str = "networkx_defence_graph.png") -> None:
    """Rysuje zagregowany graf kontaktów; para z fałszywą wiadomością jest czerwona."""
    H = nx.DiGraph()
    for node, attrs in graph.nodes(data=True):
        H.add_node(node, **attrs)
    for u, v, _key, attrs in graph.edges(keys=True, data=True):
        if H.has_edge(u, v):
            H[u][v]["count"] += 1
            H[u][v]["has_false"] = H[u][v]["has_false"] or attrs["is_false"]
        else:
            H.add_edge(u, v, count=1, has_false=attrs["is_false"])

    pos = nx.spring_layout(H, seed=SEED, k=1.35, iterations=150)
    fig, ax = plt.subplots(figsize=(15, 10))
    edge_colors = ["#d62728" if H[u][v]["has_false"] else "#8a96a3" for u, v in H.edges()]
    widths = [1.1 + 0.45 * H[u][v]["count"] for u, v in H.edges()]
    nx.draw_networkx_edges(
        H, pos, ax=ax, edge_color=edge_colors, width=widths,
        arrows=True, arrowsize=15, alpha=0.72, connectionstyle="arc3,rad=0.08",
        min_source_margin=10, min_target_margin=12,
    )
    styles = {
        "influencer": ("#547A9B", "o", 850),
        "fake": ("#C9873A", "X", 1000),
        "recipient": ("#6F9B83", "s", 520),
    }
    for role, (color, marker, size) in styles.items():
        nodes = [n for n, d in H.nodes(data=True) if d["role"] == role]
        nx.draw_networkx_nodes(H, pos, nodelist=nodes, node_color=color, node_shape=marker,
                               node_size=size, edgecolors="white", linewidths=1.5, ax=ax)
    labels = {n: f"{n}\n{H.nodes[n]['name']}" for n in H.nodes()}
    nx.draw_networkx_labels(H, pos, labels=labels, font_size=8, font_weight="medium", ax=ax)
    legend = [
        Line2D([0], [0], marker="o", color="w", label="Prawdziwy influencer", markerfacecolor=styles["influencer"][0], markersize=11),
        Line2D([0], [0], marker="X", color="w", label="Podejrzane konto", markerfacecolor=styles["fake"][0], markersize=11),
        Line2D([0], [0], marker="s", color="w", label="Odbiorca", markerfacecolor=styles["recipient"][0], markersize=10),
        Line2D([0], [0], color="#8a96a3", lw=2, label="Wiadomość prawdziwa / zwykły kontakt"),
        Line2D([0], [0], color="#d62728", lw=2, label="Co najmniej jedna fałszywa wiadomość"),
    ]
    ax.legend(handles=legend, loc="upper left", frameon=True, fontsize=9)
    ax.set_title("Demonstracyjna sieć przepływu informacji", fontsize=16, pad=18)
    ax.text(0.01, 0.01, "Strzałka: nadawca → odbiorca. Kolor krawędzi dotyczy pary kont.",
            transform=ax.transAxes, fontsize=9, color="#444")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(filename, dpi=180, bbox_inches="tight")
    print(f"\nWykres zapisano jako: {filename}")
    plt.show()



def create_case_study_gif(filename: str = "networkx_defence_case_study.gif") -> None:
    """Tworzy animację: influencerzy → odbiorcy → interakcje → fałszywa wiadomość.

    Układ węzłów jest stały, żeby na kolejnych klatkach można było śledzić
    rozbudowę tej samej sieci. Zapis wymaga Pillow (dostarczanego zwykle z Matplotlib).
    """
    positions = {
        "I1": (0.12, 0.84), "I2": (0.31, 0.84), "I3": (0.50, 0.84),
        "I4": (0.69, 0.84), "I5": (0.88, 0.84),
        "F1": (0.95, 0.61),
    }
    for i in range(1, 6):
        positions[f"R{i:02d}"] = (0.10 + (i - 1) * 0.20, 0.37)
        positions[f"R{i + 5:02d}"] = (0.10 + (i - 1) * 0.20, 0.14)

    all_nodes = set(G.nodes())
    states: list[dict[str, Any]] = []
    real_influencers = [n for n in G.nodes() if G.nodes[n]["role"] == "influencer"]
    visible_nodes: set[str] = set(real_influencers)
    visible_edges: list[dict[str, Any]] = []

    def add_state(title: str, active: set[str] | None = None) -> None:
        states.append({
            "title": title,
            "nodes": set(visible_nodes),
            "edges": list(visible_edges),
            "active": set(active or set()),
        })

    add_state("Etap 1 — sieć prawdziwych influencerów")

    # Etap 2: wszyscy odbiorcy pojawiają się jednocześnie.
    recipients = sorted(n for n in G.nodes() if G.nodes[n]["role"] == "recipient")
    visible_nodes.update(recipients)
    add_state("Etap 2 — dołączają wszyscy odbiorcy")

    edge_records = [
        {"source": u, "target": v, **data}
        for u, v, _key, data in G.edges(keys=True, data=True)
    ]
    # Etap 3a: prawdziwi influencerzy wchodzą w interakcje.
    influencer_edges = [e for e in edge_records
                        if G.nodes[e["source"]]["role"] == "influencer"
                        and G.nodes[e["target"]]["role"] == "influencer"
                        and not e["is_false"]]
    seen_pairs: set[tuple[str, str]] = set()
    for edge in influencer_edges:
        pair = (edge["source"], edge["target"])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            visible_edges.append(edge)
    add_state("Etap 3 — influencerzy wymieniają się informacjami")

    # Etap 3b: influencerzy publikują do swoich odbiorców, partiami.
    for influencer in real_influencers:
        group = [e for e in edge_records
                 if e["source"] == influencer
                 and G.nodes[e["target"]]["role"] == "recipient"
                 and not e["is_false"]]
        for edge in group:
            pair = (edge["source"], edge["target"])
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                visible_edges.append(edge)
        add_state(f"Etap 3 — {G.nodes[influencer]['name']} kontaktuje się z odbiorcami")

    # Etap 3c: odbiorcy zaczynają przekazywać sobie informacje.
    recipient_edges = [e for e in edge_records
                       if G.nodes[e["source"]]["role"] == "recipient"
                       and G.nodes[e["target"]]["role"] == "recipient"
                       and not e["is_false"]]
    for edge in recipient_edges:
        pair = (edge["source"], edge["target"])
        if pair not in seen_pairs:
            seen_pairs.add(pair)
            visible_edges.append(edge)
    add_state("Etap 3 — odbiorcy wchodzą we wzajemne interakcje")

    # Na końcu pojawia się podszywające konto i inicjuje fałszywą wiadomość.
    fake_id = next(n for n in G.nodes() if G.nodes[n]["role"] == "fake")
    visible_nodes.add(fake_id)
    add_state("Etap 4 — pojawia się konto podszywające się pod influencerkę")
    false_messages = [e for e in edge_records if e["is_false"]]
    selected = false_messages[0]
    seed_node = selected["source"]
    visible_edges.append(selected)
    add_state(f"Etap 4 — fałszywa wiadomość dociera do {selected['target']}", {seed_node})

    _active, _received, attempts = run_independent_cascade(G, seed_node, selected, seed=SEED)
    active_so_far = {seed_node}
    for attempt in attempts:
        edge = {
            "source": attempt["source"], "target": attempt["target"],
            "is_false": True, "adopted": attempt["adopted"],
            "probability": attempt["p"],
        }
        # Sukces: czerwona strzałka; niepowodzenie: szara, przerywana próba.
        visible_edges.append(edge)
        if attempt["adopted"]:
            active_so_far.add(attempt["target"])
        label = "podał dalej" if attempt["adopted"] else "nie podał dalej"
        add_state(
            f"Etap 5 — {attempt['source']} → {attempt['target']}: {label} "
            f"(p={attempt['p']:.0%})",
            active_so_far,
        )
    add_state("Koniec symulacji — czerwone węzły przekazały fałszywą wiadomość", active_so_far)

    fig, ax = plt.subplots(figsize=(12, 7), facecolor="#f7f8fa")
    fig.subplots_adjust(left=0.03, right=0.97, top=0.88, bottom=0.08)

    def draw_frame(frame_index: int) -> None:
        ax.clear()
        state = states[frame_index]
        ax.set_facecolor("#f7f8fa")
        ax.set_xlim(0, 1.02)
        ax.set_ylim(0.02, 1.02)
        ax.axis("off")
        ax.set_title(state["title"], fontsize=14, weight="bold", pad=16, color="#263238")

        for edge in state["edges"]:
            u, v = edge["source"], edge["target"]
            if u not in state["nodes"] or v not in state["nodes"]:
                continue
            x1, y1 = positions[u]
            x2, y2 = positions[v]
            is_false = edge.get("is_false", False)
            adopted = edge.get("adopted", True)
            color = "#d62728" if is_false and adopted else ("#ef8a8a" if is_false else "#a3adb8")
            style = "-" if adopted else "--"
            rad = 0.10 if x2 >= x1 else -0.10
            patch = FancyArrowPatch(
                (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                linewidth=2.0 if is_false else 1.1, color=color, linestyle=style,
                connectionstyle=f"arc3,rad={rad}", shrinkA=17, shrinkB=17,
                alpha=0.86 if adopted else 0.55, zorder=1,
            )
            ax.add_patch(patch)

        for node in sorted(state["nodes"]):
            attrs = G.nodes[node]
            x, y = positions[node]
            role = attrs["role"]
            color = {"influencer": "#547A9B", "fake": "#C9873A", "recipient": "#6F9B83"}[role]
            if node in state["active"] and node != seed_node:
                color = "#d62728"
            marker = "X" if role == "fake" else ("o" if role == "influencer" else "s")
            size = 850 if role != "recipient" else 580
            ax.scatter([x], [y], s=size, marker=marker, color=color,
                       edgecolors="white", linewidths=1.5, zorder=3)
            label = attrs["name"] if role != "recipient" else node
            ax.text(x, y - 0.055, label, ha="center", va="top", fontsize=8,
                    color="#263238", zorder=4)

        ax.text(0.01, 0.01,
                "Niebieski: influencer  |  zielony: odbiorca  |  pomarańczowy X: konto podszywające się  |  czerwony: fałszywa wiadomość / aktywny odbiorca",
                transform=ax.transAxes, fontsize=8, color="#455a64")

    animation = FuncAnimation(fig, draw_frame, frames=len(states), interval=900, repeat=False)
    animation.save(filename, writer=PillowWriter(fps=1), dpi=90)
    plt.close(fig)
    print(f"Animację GIF zapisano jako: {filename} ({len(states)} klatek)")

def main() -> None:
    # Kontrola zakresu wektorów przywiązania do tematów.
    for node_id, attrs in G.nodes(data=True):
        vector = attrs["attachment"]
        assert vector.shape == (len(TOPICS),) and np.all((0 <= vector) & (vector <= 1)), node_id

    print("SYNTHETYCZNA SIEĆ")
    print(f"Węzły: {G.number_of_nodes()} (6 kont influencerów, w tym 1 podejrzane, + 10 odbiorców)")
    print(f"Wiadomości / skierowane krawędzie: {G.number_of_edges()}")
    print("Kolejność współrzędnych wektorów: " + ", ".join(TOPICS))
    print("\nPrzykładowe wektory przywiązania do tematów:")
    for node_id in ["I1", "F1", "R01", "R06"]:
        values = ", ".join(f"{topic}={value:.2f}" for topic, value in zip(TOPICS, G.nodes[node_id]["attachment"]))
        print(f"  {node_id} ({G.nodes[node_id]['handle']}): {values}")

    findings = impersonation_scan(G)
    print("\nWYNIK HEURYSTYKI PODSZYWANIA SIĘ (próg 0.70)")
    if findings:
        for item in findings:
            print(f"  {item['candidate_handle']} może podszywać się pod {item['real_handle']}: "
                  f"score={item['score']:.3f}, podobieństwo nazwy={item['name_similarity']:.2f}, "
                  f"profilu={item['profile_similarity']:.2f}")
    else:
        print("  Nie znaleziono kont powyżej progu.")

    false_messages = [d for _u, _v, _k, d in G.edges(keys=True, data=True) if d["is_false"]]
    selected = false_messages[0]
    seed_node = next(u for u, _v, _k, d in G.edges(keys=True, data=True) if d["message_id"] == selected["message_id"])
    print(f"\nSYMULACJA WIADOMOŚCI {selected['message_id']} — {selected['text']}")
    print(f"Temat: {selected['topic']}; źródło: {G.nodes[seed_node]['handle']}; fałszywa: tak")
    active, received, attempts = run_independent_cascade(G, seed_node, selected, seed=SEED)
    print("Aktywne osoby (podały dalej w symulacji): " + ", ".join(sorted(active)))
    print("Osoby, które otrzymały wiadomość albo były jej źródłem: " + ", ".join(sorted(received)))
    print("Próby przekazania:")
    for attempt in attempts:
        status = "PODAŁA DALEJ" if attempt["adopted"] else "nie podała dalej"
        print(f"  runda {attempt['round']}: {attempt['source']} → {attempt['target']}, "
              f"p={attempt['p']:.2f}: {status}")

    print("\nDEMONSTRACYJNY WYNIK PODATNOŚCI ODBIORCÓW")
    print("To prawdopodobieństwo pojedynczego przekazania w heurystyce, nie wynik treningu modelu.")
    for node_id in sorted(n for n, d in G.nodes(data=True) if d["role"] == "recipient"):
        probability = adoption_probability(G.nodes[node_id], G.nodes[seed_node], selected)
        affinity = G.nodes[node_id]["attachment"][topic_index(selected["topic"])]
        print(f"  {node_id}: {probability:.1%} (przywiązanie do tematu {selected['topic']}: {affinity:.2f})")

    create_case_study_gif()
    draw_graph(G)


if __name__ == "__main__":
    main()
