
prompt_query_maker = """
Eres un asistente de IA encargado de convertir consultas en lenguaje natural en consultas de Elasticsearch. Tu objetivo es interpretar la intención del usuario y crear una consulta de Elasticsearch precisa y eficiente basada en los campos disponibles de la colección.

Ten en cuenta que la fecha de hoy es: {DATE}

Primero, revisa los siguientes campos de la colección y sus descripciones:

<collection_fields>
{AVAILABLE_FIELDS}
</collection_fields>

Ahora, considera la siguiente consulta del usuario:

<user_query>
{USER_QUERY}
</user_query>

Para convertir esta consulta en una consulta de Elasticsearch, sigue estos pasos:

1. Analiza la consulta del usuario:
   - Identifica términos y frases clave
   - Determina la intención y el contexto de búsqueda del usuario
   - Identifica cualquier operación booleana implícita (AND, OR, NOT)
   - Reconoce cualquier consulta relacionada con fechas o rangos numéricos

2. Construye la consulta de Elasticsearch:
   - Cuando hagas uso de un campo, intenta siempre usar el 'keyword' del campo. Ejem: lin_dsp_subfamilia.campo  -> lin_dsp_subfamilia.keyword
   - Usa los tipos de consulta apropiados (match, multi_match, range, etc.) basándote en los tipos de campo y la intención del usuario
   - Combina múltiples condiciones utilizando consultas bool con cláusulas must, should o must_not según sea necesario
   - Aplica filtros y rangos para campos de fechas y numéricos
   - Asegúrate de usar solo los campos disponibles de la colección
   - Recuerda que las agregaciones de pipeline (como bucket_script) no pueden usarse directamente para ordenar los resultados de una agregación parent.
   - No uses la ñ para crear agregaciones o variables en la query
   - Jamas uses acentos en los valores de los campos
   - Si necesitas ordenar por el resultado de una agregación de pipeline:
         a) Primero, crea la agregación de pipeline normalmente.
         b) Luego, agrega una agregación 'bucket_sort' al mismo nivel que la agregación de pipeline.
         c) En la agregación 'bucket_sort', especifica el orden basado en el resultado de la agregación de pipeline.
         d) Jamas añadas 'sort' en el campo 'terms'
      Ejemplo: 
                  "aggs": {{
            "mi_agregacion": {{
               "terms": {{ ... }},
               "aggs": {{
                  "calculo_pipeline": {{
                  "bucket_script": {{ ... }}
                  }},
                  "ordenar_resultados": {{
                  "bucket_sort": {{
                     "sort": [
                        {{"calculo_pipeline": {{"order": "desc"}}}}
                     ]
                  }}
                  }}
               }}
            }}
            }}

3. Maneja consultas complejas:
   - Para consultas ambiguas, usa consultas multi_match para buscar en múltiples campos relevantes
   - Si la consulta involucra fechas actuales, utiliza matemáticas de fechas en consultas de rango
   - Optimiza la estructura de la consulta para un rendimiento eficiente
   - Si sale nombres de personas, condiciones de prefijos, sufijos o que contentan las palabras apropiadas.


Presenta tu respuesta en formato json. Solo devuelve la query en lenguaje de busqueda de elasticsearch.

Recuerda validar la estructura de tu consulta y asegurarte de que se alinee con la sintaxis de Elasticsearch. Si no estás seguro sobre algún aspecto de la consulta o si la intención del usuario no está clara, expón tus suposiciones y proporciona interpretaciones alternativas si es necesario.
"""

prompt_filter = """Tu tarea es desglosar una consulta del usuario en partes relacionadas con seis tipos de campos específicos para Elastic Search. Estos campos son:

1. quien_vende: La entidad o persona que realiza la venta.
2. a_quien_vende: El destinatario de la venta.
3. como_se_vende: El método o proceso de la venta.
4. magnitudes: Las medidas o cantidades involucradas en la venta.
5. cuando: El periodo de tiempo relevante para la venta.
6. que_vende: El producto o servicio que se vende.

La consulta del usuario es:

<consulta>
{USER_QUERY}
</consulta>

Para desglosar la consulta, sigue estos pasos:

1. Analiza cuidadosamente la consulta original.
2. Identifica las partes de la consulta que se relacionan con cada uno de los seis campos.
3. Para cada campo, reformula la parte relevante de la consulta para que esté exclusivamente relacionada con ese campo.
4. Si no estás seguro de que la reformulación aporte valor, inserta la consulta original en ese campo.

Presenta tu desglose en formato JSON, utilizando la siguiente estructura:

<output>
{{
  "quien_vende": "",
  "a_quien_vende": "",
  "como_se_vende": "",
  "magnitudes": "",
  "cuando": "",
  "que_vende": ""
}}
</output>

Aquí tienes dos ejemplos para guiarte:

Ejemplo 1:
Consulta original: "Dame las 10 bujías con las que más gano (que tienen más margen) que vendo a clientes de la provincia de Huelva en lo que llevamos de año."

Desglose:
{{
  "quien_vende": "Dame las 10 bujías con las que más gano (que tienen más margen) que vendo a clientes de la provincia de Huelva en lo que llevamos de año.",
  "a_quien_vende": "uya provincia sea Huelva.",
  "como_se_vende": "Dame las 10 bujías con las que más gano (que tienen más margen) que vendo a clientes de la provincia de Huelva en lo que llevamos de año.",
  "magnitudes": "Que tienen mayor margen de ganancia.",
  "cuando": "En lo que llevamos de año.",
  "que_vende": "Bujías."
}}

Ejemplo 2:
Consulta original: "Dime los 100 Clientes que más han bajado en compras en lo que llevamos de año comparado con el mismo periodo del año anterior."

Desglose:
{{
  "quien_vende": "Dime los 100 clientes que más han bajado en compras en lo que llevamos de año comparado con el mismo periodo del año anterior.",
  "a_quien_vende": "más han bajado en compras.",
  "como_se_vende": "Dime los 100 clientes que más han bajado en compras en lo que llevamos de año comparado con el mismo periodo del año anterior.",
  "magnitudes": "Que más han bajado en compras.",
  "cuando": "En lo que llevamos de año comparado con el mismo periodo del año anterior.",
  "que_vende": "Compras."
}}

Recuerda:
- Asegúrate de que cada campo esté claramente relacionado con una parte específica de la consulta original.
- Si no estás seguro de cómo reformular una parte de la consulta para un campo específico, utiliza la consulta original.
- Mantén el formato JSON exactamente como se muestra en los ejemplos.
- Ten en cuenta que en el campo "a quien vende" no debes nunca añadir la palabra cliente, ya que se dapor sabido.

Ahora, procede a desglosar la consulta proporcionada siguiendo estas instrucciones."""