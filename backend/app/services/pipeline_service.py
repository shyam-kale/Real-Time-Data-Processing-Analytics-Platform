from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.pipeline import Pipeline, PipelineNode, PipelineEdge, PipelineRun, PipelineStatus, RunStatus
from app.schemas.pipeline import PipelineCreate, PipelineUpdate
from app.services.activity_service import log_activity


async def create_pipeline(db: AsyncSession, org_id: str, user_id: str, data: PipelineCreate) -> Pipeline:
    pipeline = Pipeline(
        organization_id=org_id,
        created_by=user_id,
        name=data.name,
        description=data.description,
        tags=data.tags,
    )
    db.add(pipeline)
    await db.flush()

    node_id_map = {}
    for n in data.nodes:
        node = PipelineNode(
            id=n.id,
            pipeline_id=pipeline.id,
            node_type=n.node_type,
            label=n.label,
            config=n.config,
            position_x=n.position.x,
            position_y=n.position.y,
        )
        db.add(node)
        node_id_map[n.id] = node

    await db.flush()

    for e in data.edges:
        edge = PipelineEdge(
            id=e.id,
            pipeline_id=pipeline.id,
            source_node_id=e.source,
            target_node_id=e.target,
        )
        db.add(edge)

    await log_activity(db, org_id, user_id, "pipeline.created", "pipeline", pipeline.id, pipeline.name)
    return pipeline


async def update_pipeline(
    db: AsyncSession, pipeline_id: str, org_id: str, user_id: str, data: PipelineUpdate
) -> Pipeline:
    pipeline = await get_pipeline(db, pipeline_id, org_id)

    if data.name is not None:
        pipeline.name = data.name
    if data.description is not None:
        pipeline.description = data.description
    if data.status is not None:
        pipeline.status = data.status
    if data.tags is not None:
        pipeline.tags = data.tags

    if data.nodes is not None:
        # Replace nodes
        existing_nodes = await db.execute(
            select(PipelineNode).where(PipelineNode.pipeline_id == pipeline_id)
        )
        for node in existing_nodes.scalars():
            await db.delete(node)
        existing_edges = await db.execute(
            select(PipelineEdge).where(PipelineEdge.pipeline_id == pipeline_id)
        )
        for edge in existing_edges.scalars():
            await db.delete(edge)
        await db.flush()

        for n in data.nodes:
            node = PipelineNode(
                id=n.id,
                pipeline_id=pipeline.id,
                node_type=n.node_type,
                label=n.label,
                config=n.config,
                position_x=n.position.x,
                position_y=n.position.y,
            )
            db.add(node)

        await db.flush()

        if data.edges:
            for e in data.edges:
                edge = PipelineEdge(
                    id=e.id,
                    pipeline_id=pipeline.id,
                    source_node_id=e.source,
                    target_node_id=e.target,
                )
                db.add(edge)

    await log_activity(db, org_id, user_id, "pipeline.updated", "pipeline", pipeline.id, pipeline.name)
    return pipeline


async def get_pipeline(db: AsyncSession, pipeline_id: str, org_id: str) -> Pipeline:
    result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.organization_id == org_id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(404, "Pipeline not found")
    return pipeline


async def list_pipelines(
    db: AsyncSession, org_id: str, skip: int = 0, limit: int = 50
) -> tuple[List[Pipeline], int]:
    q = select(Pipeline).where(Pipeline.organization_id == org_id).order_by(Pipeline.created_at.desc())
    cq = select(func.count()).select_from(Pipeline).where(Pipeline.organization_id == org_id)
    result = await db.execute(q.offset(skip).limit(limit))
    count = await db.execute(cq)
    return result.scalars().all(), count.scalar()


async def delete_pipeline(db: AsyncSession, pipeline_id: str, org_id: str, user_id: str) -> None:
    pipeline = await get_pipeline(db, pipeline_id, org_id)
    await log_activity(db, org_id, user_id, "pipeline.deleted", "pipeline", pipeline_id, pipeline.name)
    await db.delete(pipeline)


async def list_runs(
    db: AsyncSession, org_id: str, pipeline_id: Optional[str] = None, skip: int = 0, limit: int = 50
) -> tuple[List[PipelineRun], int]:
    q = (
        select(PipelineRun)
        .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .where(Pipeline.organization_id == org_id)
    )
    cq = (
        select(func.count())
        .select_from(PipelineRun)
        .join(Pipeline, Pipeline.id == PipelineRun.pipeline_id)
        .where(Pipeline.organization_id == org_id)
    )
    if pipeline_id:
        q = q.where(PipelineRun.pipeline_id == pipeline_id)
        cq = cq.where(PipelineRun.pipeline_id == pipeline_id)

    q = q.order_by(PipelineRun.created_at.desc())
    result = await db.execute(q.offset(skip).limit(limit))
    count = await db.execute(cq)
    return result.scalars().all(), count.scalar()
