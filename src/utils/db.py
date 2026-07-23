import bw2data as bd
import lca_algebraic as agb
import logging

cur_main_tech = None


def make_main_tech(db_name=None):
    """
    Redirect all technosphere exchanges pointing to the current main
    technosphere database to the corresponding activities in another
    database (typically a Premise scenario database).

    Premise regenerates Brightway activity codes, so matching is done using:
        (name, reference product, location, unit)

    Parameters
    ----------
    db_name : str, optional
        Target technosphere database. If None, reset to the default
        ecoinvent background database.
    """

    global cur_main_tech

    default_db = agb.database._listTechBackgroundDbs()[0]

    if cur_main_tech is None:
        cur_main_tech = default_db

    if db_name is None:
        db_name = default_db

    if db_name == cur_main_tech:
        logging.warning("Already using %s", db_name)
        return

    old_db = cur_main_tech

    logging.info(
        "Mapping technosphere: %s → %s",
        old_db,
        db_name,
    )

    premise_db = bd.Database(db_name)

    # Build lookup table for target Premise database
    # Premise does not preserve Brightway codes, but preserves these fields.
    premise_lookup = {}

    for act in premise_db:
        key = (
            act["name"],
            act.get("reference product"),
            act["location"],
            act["unit"],
        )

        # In case of duplicates, keep first occurrence
        if key not in premise_lookup:
            premise_lookup[key] = act.key

    changed = 0
    missing = 0

    for database_name in bd.databases:

        # Ignore biosphere databases
        if "biosphere" in database_name:
            continue

        # Do not modify the target database itself
        if database_name == agb.database._listTechBackgroundDbs()[0]:
            continue

        # Avoid modifying mapping/helper databases
        if database_name.startswith("ei_"):
            continue

        logging.debug("Updating %s", database_name)

        db = bd.Database(database_name)

        for act in db:

            modified = False

            for exc in act.technosphere():

                # Only replace exchanges pointing to the old main database
                if exc.input["database"] != old_db:
                    continue

                old_act = exc.input

                key = (
                    old_act["name"],
                    old_act.get("reference product"),
                    old_act["location"],
                    old_act["unit"],
                )

                target = premise_lookup.get(key)

                if target is None:
                    missing += 1
                    logging.warning(
                        "No match: %s | %s | %s | %s",
                        old_act["name"],
                        old_act.get("reference product"),
                        old_act["location"],
                        old_act["unit"],
                    )
                    continue

                exc.input = target
                exc.save()

                changed += 1
                modified = True

            if modified:
                act.save()

    cur_main_tech = db_name

    logging.info(
        "Changed main technosphere: %s → %s (%d exchanges changed, %d missing)",
        old_db,
        db_name,
        changed,
        missing,
    )