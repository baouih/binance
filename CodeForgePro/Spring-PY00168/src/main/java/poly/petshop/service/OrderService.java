package poly.petshop.service;

import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import poly.petshop.domain.Order;
import poly.petshop.repository.OrderRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Service
public class OrderService {
    private static final Logger logger = LoggerFactory.getLogger(OrderService.class);
    private final OrderRepository orderRepository;

    public OrderService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public List<Order> findAll() {
        return orderRepository.findAll();
    }

    public Order findbyOrders(int orderId) {
        logger.debug("Finding order with ID: {}", orderId);
        return orderRepository.findByOrderId(orderId);
    }

    @Transactional
    public Order handleSaveOrder(Order order) {
        logger.debug("Saving order: {}", order);
        return orderRepository.save(order);
    }

    @Transactional
    public void deleteOrder(int orderId) {
        logger.debug("Deleting order with ID: {}", orderId);
        orderRepository.deleteById(orderId);
    }
}