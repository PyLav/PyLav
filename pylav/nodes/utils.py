async def sort_key_nodes(node: Node, region: str = None) -> float:
    return await node.penalty_with_region(region)
