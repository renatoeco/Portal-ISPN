from funcoes_auxiliares import conectar_mongo_portal_ispn
from bson import ObjectId


######################################################################################################
# CONEXÃO COM O BANCO DE DADOS MONGODB
######################################################################################################


db = conectar_mongo_portal_ispn()
estatistica = db["estatistica"]  # Coleção de estatísticas
programas_areas = db["programas_areas"]  # Coleção de notícias monitoradas


# Itera por todos os documentos
for doc in programas_areas.find():
    updated_programas_areas = []
    for item in doc["programas_areas"]:
        novo_id = ObjectId()  # gera novo ObjectId real
        item["id"] = novo_id  # salva como ObjectId (não string!)
        updated_programas_areas.append(item)
    
    # Atualiza o documento no banco
    programas_areas.update_one(
        {"_id": doc["_id"]},
        {"$set": {"programas_areas": updated_programas_areas}}
    )
    print(f"Documento {doc['_id']} atualizado com novos ObjectIds.")

print("Atualização concluída!")