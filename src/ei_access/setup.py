import bw2io
import bw2data as bd

def setup_ecoinvent_database(eia):
    if any(f"ecoinvent-{eia.version}-{eia.system_model}" in key for key in bd.databases.keys()):
        return
    if  eia.version != "None" and eia.system_model != "None":
        if eia.path != "None":
            eicut = bw2io.SingleOutputEcospold2Importer(eia.path, f"ecoinvent-{eia.version}-{eia.system_model}")
            eicut.apply_strategies()
            eicut.statistics()
            eicut.write_database()    
            return

        if eia.username != "None" and eia.password:
            # Download the dabase    
            bw2io.import_ecoinvent_release(version = eia.version,
                                        system_model = eia.system_model,
                                        username = eia.username,
                                        password = eia.password,
                                    ) 
            return
    raise ValueError(f"Please fill EcoInvent database access mean in \src\ei_access\setup.py")
