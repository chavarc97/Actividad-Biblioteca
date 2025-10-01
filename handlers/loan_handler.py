"""
Handlers para préstamos y devoluciones de libros
Basado en el código original pero refactorizado con principios SOLID
"""
import logging
from typing import Optional

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response

from services.book_service import BookService
from services.loan_service import LoanService
from helpers.utils import ResponsePhrases, DateUtils, TextUtils
from factories.service_factory import get_service_factory


logger = logging.getLogger(__name__)


class LoanBookIntentHandler(AbstractRequestHandler):
    """
    Handler para prestar libros
    
    Principios aplicados:
    - Single Responsibility: Solo maneja préstamos
    - Dependency Inversion: Usa servicios abstractos
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """
        Verifica si puede manejar la request
        
        Args:
            handler_input: Input del handler
        
        Returns:
            True si puede manejar la request
        """
        return ask_utils.is_intent_name("PrestarLibroIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el intent de prestar libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            # Obtener servicios
            book_service = self.service_factory.get_book_service(handler_input)
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener valores de slots
            titulo = ask_utils.get_slot_value(handler_input, "titulo")
            nombre_persona = ask_utils.get_slot_value(handler_input, "nombre_persona")
            
            if not titulo:
                return self._request_book_title(handler_input, book_service, user_id)
            
            # Crear el préstamo usando el servicio
            success, message, loan = loan_service.create_loan(
                user_id=user_id,
                book_title=titulo,
                person_name=nombre_persona
            )
            
            if success:
                return self._handle_loan_success(handler_input, loan, book_service, user_id)
            else:
                return self._handle_loan_failure(handler_input, message, book_service, user_id)
            
        except Exception as e:
            logger.error(f"Error en LoanBookHandler: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _request_book_title(self, handler_input, book_service: BookService, user_id: str) -> Response:
        """
        Solicita el título del libro a prestar
        
        Args:
            handler_input: Input del handler
            book_service: Servicio de libros
            user_id: ID del usuario
        
        Returns:
            Response solicitando título
        """
        # Obtener libros disponibles para sugerir
        available_books = book_service.get_available_books(user_id)
        
        prompts = [
            "¡Claro! ¿Qué libro quieres prestar?",
            "Por supuesto. ¿Cuál libro vas a prestar?",
            "¡Perfecto! ¿Qué libro necesitas prestar?"
        ]
        
        speak_output = ResponsePhrases.get_random_phrase(prompts)
        
        if available_books:
            # Sugerir algunos libros disponibles
            sample_books = available_books[:2]
            titles = [book.titulo for book in sample_books]
            
            if len(available_books) == 1:
                speak_output += f" Tienes disponible '{titles[0]}'."
            elif len(available_books) <= 3:
                speak_output += f" Tienes disponibles: {TextUtils.format_list_natural([f'\'{t}\'' for t in titles], 'y')}."
            else:
                speak_output += f" Por ejemplo, tienes disponibles: {TextUtils.format_list_natural([f'\'{t}\'' for t in titles], 'y')}."
        
        ask_output = "¿Cuál es el título del libro que quieres prestar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_loan_success(self, handler_input, loan, book_service: BookService, user_id: str) -> Response:
        """
        Maneja el éxito al crear un préstamo
        
        Args:
            handler_input: Input del handler
            loan: Préstamo creado
            book_service: Servicio de libros
            user_id: ID del usuario
        
        Returns:
            Response de éxito
        """
        # Respuesta natural variada
        confirmacion = ResponsePhrases.get_random_phrase(ResponsePhrases.CONFIRMACIONES)
        persona_text = f" a {loan.persona}" if loan.persona != "un amigo" else ""
        fecha_limite = DateUtils.format_date_spanish(loan.fecha_limite)
        
        speak_output = f"{confirmacion} He registrado el préstamo de '{loan.titulo}'{persona_text}. "
        speak_output += f"La fecha de devolución es el {fecha_limite}. "
        
        # Informar cuántos libros disponibles quedan
        available_books = book_service.get_available_books(user_id)
        disponibles_count = len(available_books)
        
        if disponibles_count > 0:
            books_text = TextUtils.pluralize(disponibles_count, "libro disponible", "libros disponibles")
            speak_output += f"Te quedan {disponibles_count} {books_text}. "
        else:
            speak_output += "Ya no tienes más libros disponibles para prestar. "
        
        speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
        ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_loan_failure(self, handler_input, message: str, 
                           book_service: BookService, user_id: str) -> Response:
        """
        Maneja el fallo al crear un préstamo
        
        Args:
            handler_input: Input del handler
            message: Mensaje de error del servicio
            book_service: Servicio de libros
            user_id: ID del usuario
        
        Returns:
            Response de error con sugerencias
        """
        speak_output = f"Hmm, {message}. "
        
        # Sugerir libros disponibles si los hay
        available_books = book_service.get_available_books(user_id)
        if available_books:
            sample_books = available_books[:2]
            titles = [f"'{book.titulo}'" for book in sample_books]
            
            speak_output += f"Tienes disponibles: {TextUtils.format_list_natural(titles, 'y')}. "
            ask_output = "¿Cuál quieres prestar?"
        else:
            speak_output += "No tienes libros disponibles para prestar en este momento."
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_error(self, handler_input) -> Response:
        """
        Maneja errores generales
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de error
        """
        speak_output = "Ups, tuve un problema registrando el préstamo. ¿Lo intentamos de nuevo?"
        ask_output = "¿Qué libro quieres prestar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """
        Extrae el user ID del handler input
        
        Args:
            handler_input: Input del handler
        
        Returns:
            User ID
        """
        return handler_input.request_envelope.context.system.user.user_id


class ReturnBookIntentHandler(AbstractRequestHandler):
    """
    Handler para devolver libros prestados
    
    Principios aplicados:
    - Single Responsibility: Solo maneja devoluciones
    - Dependency Inversion: Usa servicios abstractos
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """
        Verifica si puede manejar la request
        
        Args:
            handler_input: Input del handler
        
        Returns:
            True si puede manejar la request
        """
        return ask_utils.is_intent_name("DevolverLibroIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el intent de devolver libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            # Obtener servicios
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener valores de slots
            titulo = ask_utils.get_slot_value(handler_input, "titulo")
            id_prestamo = ask_utils.get_slot_value(handler_input, "id_prestamo")
            
            if not titulo and not id_prestamo:
                return self._request_book_title(handler_input, loan_service, user_id)
            
            # Procesar la devolución usando el servicio
            success, message, loan = loan_service.return_loan(
                user_id=user_id,
                book_title=titulo,
                loan_id=id_prestamo
            )
            
            if success:
                return self._handle_return_success(handler_input, loan, loan_service, user_id)
            else:
                return self._handle_return_failure(handler_input, message, loan_service, user_id)
            
        except Exception as e:
            logger.error(f"Error en ReturnBookHandler: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _request_book_title(self, handler_input, loan_service: LoanService, user_id: str) -> Response:
        """
        Solicita el título del libro a devolver
        
        Args:
            handler_input: Input del handler
            loan_service: Servicio de préstamos
            user_id: ID del usuario
        
        Returns:
            Response solicitando título
        """
        # Obtener préstamos activos para sugerir
        active_loans = loan_service.get_active_loans(user_id)
        
        prompts = [
            "¡Qué bien! ¿Qué libro te devolvieron?",
            "Perfecto, vamos a registrar la devolución. ¿Cuál libro es?",
            "¡Excelente! ¿Qué libro estás devolviendo?"
        ]
        
        speak_output = ResponsePhrases.get_random_phrase(prompts)
        
        if active_loans:
            if len(active_loans) == 1:
                loan = active_loans[0]
                speak_output += f" Solo tienes prestado '{loan.titulo}' a {loan.persona}."
            else:
                sample_loans = active_loans[:2]
                descriptions = [f"'{loan.titulo}' a {loan.persona}" for loan in sample_loans]
                speak_output += f" Tienes prestados: {TextUtils.format_list_natural(descriptions, 'y')}."
        
        ask_output = "¿Cuál es el título del libro que te devolvieron?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_return_success(self, handler_input, loan, loan_service: LoanService, user_id: str) -> Response:
        """
        Maneja el éxito al procesar una devolución
        
        Args:
            handler_input: Input del handler
            loan: Préstamo devuelto
            loan_service: Servicio de préstamos
            user_id: ID del usuario
        
        Returns:
            Response de éxito
        """
        # Respuesta natural variada
        confirmacion = ResponsePhrases.get_random_phrase(ResponsePhrases.CONFIRMACIONES)
        speak_output = f"{confirmacion} He registrado la devolución de '{loan.titulo}'. "
        
        # Determinar si fue devuelto a tiempo
        on_time = loan.fue_devuelto_a_tiempo()
        if on_time:
            time_phrases = [
                "¡Fue devuelto a tiempo!",
                "¡Excelente puntualidad!",
                "¡Regresó en fecha!"
            ]
            speak_output += ResponsePhrases.get_random_phrase(time_phrases)
        else:
            speak_output += "Fue devuelto un poco tarde, pero no hay problema."
        
        speak_output += " Espero que lo hayan disfrutado. "
        
        # Informar préstamos restantes
        remaining_loans = loan_service.get_active_loans(user_id)
        if remaining_loans:
            loans_count = len(remaining_loans)
            loans_text = TextUtils.pluralize(loans_count, "libro prestado", "libros prestados")
            speak_output += f"Aún tienes {loans_count} {loans_text}. "
        
        speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
        ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_return_failure(self, handler_input, message: str, 
                             loan_service: LoanService, user_id: str) -> Response:
        """
        Maneja el fallo al procesar una devolución
        
        Args:
            handler_input: Input del handler
            message: Mensaje de error del servicio
            loan_service: Servicio de préstamos
            user_id: ID del usuario
        
        Returns:
            Response de error con sugerencias
        """
        speak_output = f"Hmm, {message}. "
        
        # Sugerir préstamos activos si los hay
        active_loans = loan_service.get_active_loans(user_id)
        if active_loans:
            if len(active_loans) == 1:
                loan = active_loans[0]
                speak_output += f"Solo tienes prestado '{loan.titulo}' a {loan.persona}. ¿Es ese?"
            else:
                sample_loans = active_loans[:3]
                titles = [f"'{loan.titulo}'" for loan in sample_loans]
                speak_output += f"Tienes prestados: {TextUtils.format_list_natural(titles, 'y')}. ¿Cuál de estos es?"
            
            ask_output = "¿Cuál libro quieres devolver?"
        else:
            speak_output += "No tienes libros prestados en este momento."
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_error(self, handler_input) -> Response:
        """
        Maneja errores generales
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de error
        """
        speak_output = "Tuve un problema registrando la devolución. ¿Lo intentamos de nuevo?"
        ask_output = "¿Qué libro quieres devolver?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """
        Extrae el user ID del handler input
        
        Args:
            handler_input: Input del handler
        
        Returns:
            User ID
        """
        return handler_input.request_envelope.context.system.user.user_id


class ConsultarPrestamosIntentHandler(AbstractRequestHandler):
    """
    Handler para consultar préstamos activos
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("ConsultarPrestamosIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja la consulta de préstamos activos
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            active_loans = loan_service.get_active_loans(user_id)
            overdue_loans = loan_service.get_overdue_loans(user_id)
            due_soon_loans = loan_service.get_loans_due_soon(user_id, days_threshold=2)
            
            if not active_loans:
                speak_output = "¡Excelente! No tienes ningún libro prestado en este momento. Todos están en su lugar. "
                speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            else:
                # Construir respuesta con detalles
                loans_count = len(active_loans)
                loans_text = TextUtils.pluralize(loans_count, "libro prestado", "libros prestados")
                
                speak_output = f"Déjame revisar... Tienes {loans_count} {loans_text}: "
                
                # Listar préstamos con detalles (máximo 5)
                detalles = []
                for loan in active_loans[:5]:
                    detalle = f"'{loan.titulo}' está con {loan.persona}"
                    
                    # Calcular días restantes
                    dias_restantes = loan.dias_restantes()
                    
                    if dias_restantes < 0:
                        detalle += " (¡ya venció!)"
                    elif dias_restantes == 0:
                        detalle += " (vence hoy)"
                    elif dias_restantes <= 2:
                        days_text = TextUtils.pluralize(dias_restantes, "día", "días")
                        detalle += f" (vence en {dias_restantes} {days_text})"
                    
                    detalles.append(detalle)
                
                speak_output += "; ".join(detalles) + ". "
                
                if len(active_loans) > 5:
                    speak_output += f"Y {len(active_loans) - 5} más. "
                
                # Agregar advertencias si es necesario
                if overdue_loans:
                    speak_output += "Te sugiero pedir la devolución de los libros vencidos. "
                elif due_soon_loans:
                    speak_output += "Algunos están por vencer, ¡no lo olvides! "
                
                speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(ask_output)
                    .response
            )
            
        except Exception as e:
            logger.error(f"Error en ConsultarPrestamos: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores"""
        speak_output = "Hubo un problema consultando los préstamos. ¿Intentamos de nuevo?"
        ask_output = "¿Qué más deseas hacer?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """Extrae el user ID"""
        return handler_input.request_envelope.context.system.user.user_id