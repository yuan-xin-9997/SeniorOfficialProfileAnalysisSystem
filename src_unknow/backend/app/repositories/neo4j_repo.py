from app.models.official import Official


class Neo4jRepository:
    async def merge_official(self, official: Official) -> None:
        from app.core.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run(
                """
                MERGE (o:Official {id: $id})
                SET o.name = $name,
                    o.birth_date = $birth_date,
                    o.birth_place = $birth_place,
                    o.status = $status,
                    o.level = $level,
                    o.committee_term = $committee_term
                """,
                id=str(official.id),
                name=official.name,
                birth_date=str(official.birth_date),
                birth_place=official.birth_place,
                status=official.status,
                level=official.current_level or "",
                committee_term=official.committee_term,
            )

    async def delete_official(self, official_id: str) -> None:
        from app.core.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            await session.run(
                "MATCH (o:Official {id: $id}) DETACH DELETE o",
                id=official_id,
            )

    async def merge_relationship(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        strength: float,
        **props,
    ) -> None:
        from app.core.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        label = rel_type.upper()
        async with driver.session() as session:
            await session.run(
                f"""
                MATCH (a:Official {{id: $source_id}}), (b:Official {{id: $target_id}})
                MERGE (a)-[r:{label}]->(b)
                SET r.strength = $strength,
                    r.start_year = $start_year,
                    r.end_year = $end_year,
                    r.location = $location,
                    r.department = $department
                """,
                source_id=source_id,
                target_id=target_id,
                strength=strength,
                start_year=props.get("start_year"),
                end_year=props.get("end_year"),
                location=props.get("location"),
                department=props.get("department"),
            )

    async def get_connections(self, official_id: str, min_strength: float = 0.3) -> list[dict]:
        from app.core.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(
                """
                MATCH (o:Official {id: $id})-[r]-(other:Official)
                WHERE r.strength >= $min_strength
                RETURN other.id AS id, other.name AS name, type(r) AS rel_type,
                       r.strength AS strength, r.location AS location
                ORDER BY r.strength DESC
                LIMIT 100
                """,
                id=official_id,
                min_strength=min_strength,
            )
            records = await result.data()
            return records

    async def find_shortest_path(self, from_id: str, to_id: str, max_depth: int = 3) -> list[dict]:
        from app.core.neo4j_client import get_neo4j_driver

        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run(
                f"""
                MATCH path = shortestPath(
                  (a:Official {{id: $from_id}})-[*..{max_depth}]-(b:Official {{id: $to_id}})
                )
                RETURN [n IN nodes(path) | {{id: n.id, name: n.name}}] AS nodes,
                       [rel IN relationships(path) | {{type: type(rel), strength: rel.strength}}] AS edges
                """,
                from_id=from_id,
                to_id=to_id,
            )
            record = await result.single()
            if record is None:
                return []
            return [{"nodes": record["nodes"], "edges": record["edges"]}]
