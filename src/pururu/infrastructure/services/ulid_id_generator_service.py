import ulid

from pururu.domain.services.id_generator_service import IdGeneratorService


class ULIDIdGeneratorService(IdGeneratorService):
    def next_id(self) -> str:
        return str(ulid.new())
